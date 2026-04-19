import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2, aws_iam as iam, aws_mwaa as mwaa, aws_s3 as s3
from constructs import Construct


class MwaaStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        dag_bucket: s3.Bucket,
        mwaa_env_name: str,
        airflow_version: str,
        environment_class: str,
        max_workers: int,
        min_workers: int,
        webserver_access_mode: str,
        requirements_s3_path: str = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        security_group = ec2.SecurityGroup(
            self,
            "MwaaSecurityGroup",
            vpc=vpc,
            description="Security group for MWAA environment",
            allow_all_outbound=True,
        )
        # MWAA requires workers to communicate with each other within the SG
        security_group.add_ingress_rule(
            peer=security_group,
            connection=ec2.Port.all_traffic(),
            description="Allow all traffic within MWAA security group",
        )

        execution_role = iam.Role(
            self,
            "MwaaExecutionRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("airflow.amazonaws.com"),
                iam.ServicePrincipal("airflow-env.amazonaws.com"),
            ),
            description="Execution role for MWAA environment",
        )

        execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=["s3:ListAllMyBuckets"],
                resources=["*"],
            )
        )
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject*", "s3:GetBucket*", "s3:List*"],
                resources=[dag_bucket.bucket_arn, f"{dag_bucket.bucket_arn}/*"],
            )
        )
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents",
                    "logs:GetLogEvents",
                    "logs:GetLogRecord",
                    "logs:GetLogGroupFields",
                    "logs:GetQueryResults",
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:airflow-{mwaa_env_name}-*"
                ],
            )
        )
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["logs:DescribeLogGroups"],
                resources=["*"],
            )
        )
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sqs:ChangeMessageVisibility",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl",
                    "sqs:ReceiveMessage",
                    "sqs:SendMessage",
                ],
                resources=[f"arn:aws:sqs:{self.region}:*:airflow-celery-*"],
            )
        )
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "kms:Decrypt",
                    "kms:DescribeKey",
                    "kms:GenerateDataKey*",
                    "kms:Encrypt",
                ],
                not_resources=[f"arn:aws:kms:*:{self.account}:key/*"],
                conditions={
                    "StringLike": {
                        "kms:ViaService": [
                            f"sqs.{self.region}.amazonaws.com",
                            f"s3.{self.region}.amazonaws.com",
                        ]
                    }
                },
            )
        )
        # Allow MWAA to read Airflow connections and variables from Secrets Manager
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                ],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:airflow/connections/*",
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:airflow/variables/*",
                ],
            )
        )
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["airflow:PublishMetrics"],
                resources=[
                    f"arn:aws:airflow:{self.region}:{self.account}:environment/{mwaa_env_name}"
                ],
            )
        )

        private_subnet_ids = [subnet.subnet_id for subnet in vpc.private_subnets]

        mwaa_environment = mwaa.CfnEnvironment(
            self,
            "MwaaEnvironment",
            name=mwaa_env_name,
            airflow_version=airflow_version,
            environment_class=environment_class,
            max_workers=max_workers,
            min_workers=min_workers,
            execution_role_arn=execution_role.role_arn,
            source_bucket_arn=dag_bucket.bucket_arn,
            dag_s3_path="dags/",
            requirements_s3_path=requirements_s3_path,
            webserver_access_mode=webserver_access_mode,
            airflow_configuration_options={
                "secrets.backend": "airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend",
                "secrets.backend_kwargs": '{"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables"}',
                "core.allowed_deserialization_classes": ".*",
            },
            network_configuration=mwaa.CfnEnvironment.NetworkConfigurationProperty(
                security_group_ids=[security_group.security_group_id],
                subnet_ids=private_subnet_ids,
            ),
            logging_configuration=mwaa.CfnEnvironment.LoggingConfigurationProperty(
                dag_processing_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="INFO"
                ),
                scheduler_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="INFO"
                ),
                task_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="WARNING"
                ),
                webserver_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="WARNING"
                ),
                worker_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="WARNING"
                ),
            ),
        )

        cdk.CfnOutput(
            self,
            "MwaaWebserverUrl",
            value=mwaa_environment.attr_webserver_url,
            description="Airflow UI URL — open via AWS Console > MWAA > Open Airflow UI",
        )
