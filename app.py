import aws_cdk as cdk

from src.mwaa_stack import MwaaStack
from src.network_stack import NetworkStack
from src.s3_stack import S3Stack
from src.utils import load_context_config

cdk_app = cdk.App()
env_name = cdk_app.node.try_get_context("env") or "dev"
config = load_context_config(env_name=env_name)

STACK_NAME_PREFIX = f"sage-mwaa-{env_name}"
TAGS = config.get("TAGS", {})
mwaa_config = config["MWAA"]

if TAGS:
    for key, value in TAGS.items():
        cdk.Tags.of(cdk_app).add(key, value)

network_stack = NetworkStack(
    scope=cdk_app,
    construct_id=f"{STACK_NAME_PREFIX}-network",
    vpc_cidr=config["VPC_CIDR"],
)

s3_stack = S3Stack(
    scope=cdk_app,
    construct_id=f"{STACK_NAME_PREFIX}-s3",
)

mwaa_stack = MwaaStack(
    scope=cdk_app,
    construct_id=f"{STACK_NAME_PREFIX}-mwaa",
    vpc=network_stack.vpc,
    dag_bucket=s3_stack.dag_bucket,
    mwaa_env_name=STACK_NAME_PREFIX,
    airflow_version=mwaa_config["AIRFLOW_VERSION"],
    environment_class=mwaa_config["ENV_CLASS"],
    max_workers=mwaa_config["MAX_WORKERS"],
    min_workers=mwaa_config["MIN_WORKERS"],
    webserver_access_mode=mwaa_config["WEBSERVER_ACCESS_MODE"],
    requirements_s3_path=mwaa_config.get("REQUIREMENTS_S3_PATH"),
)
mwaa_stack.add_dependency(network_stack)
mwaa_stack.add_dependency(s3_stack)

cdk_app.synth()
