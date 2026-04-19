import aws_cdk as cdk
from aws_cdk import aws_s3 as s3
from constructs import Construct


class S3Stack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.dag_bucket = s3.Bucket(
            self,
            "DagBucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            enforce_ssl=True,
        )

        cdk.CfnOutput(self, "DagBucketName", value=self.dag_bucket.bucket_name)
        cdk.CfnOutput(self, "DagBucketArn", value=self.dag_bucket.bucket_arn)
