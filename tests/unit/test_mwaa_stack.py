import aws_cdk as core
import aws_cdk.assertions as assertions

from src.network_stack import NetworkStack
from src.s3_stack import S3Stack
from src.mwaa_stack import MwaaStack


def _build_mwaa_stack():
    app = core.App()
    network = NetworkStack(app, "NetworkStack", vpc_cidr="10.254.172.0/22")
    s3 = S3Stack(app, "S3Stack")
    mwaa = MwaaStack(
        app,
        "MwaaStack",
        vpc=network.vpc,
        dag_bucket=s3.dag_bucket,
        mwaa_env_name="sage-mwaa-dev",
        airflow_version="2.10.3",
        environment_class="mw1.small",
        max_workers=2,
        min_workers=1,
        webserver_access_mode="PUBLIC_ONLY",
    )
    return assertions.Template.from_stack(mwaa)


def test_mwaa_environment_created():
    template = _build_mwaa_stack()
    template.has_resource_properties(
        "AWS::MWAA::Environment",
        {
            "Name": "sage-mwaa-dev",
            "AirflowVersion": "2.10.3",
            "EnvironmentClass": "mw1.small",
            "MaxWorkers": 2,
            "MinWorkers": 1,
            "WebserverAccessMode": "PUBLIC_ONLY",
            "DagS3Path": "dags/",
        },
    )


def test_mwaa_execution_role_created():
    template = _build_mwaa_stack()
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {"Principal": {"Service": "airflow.amazonaws.com"}}
                        )
                    ]
                )
            }
        },
    )


def test_mwaa_security_group_created():
    template = _build_mwaa_stack()
    template.resource_count_is("AWS::EC2::SecurityGroup", 1)
