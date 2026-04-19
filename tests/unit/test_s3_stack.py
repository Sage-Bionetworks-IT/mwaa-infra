import aws_cdk as core
import aws_cdk.assertions as assertions

from src.s3_stack import S3Stack


def test_dag_bucket_created():
    app = core.App()
    stack = S3Stack(app, "S3Stack")
    template = assertions.Template.from_stack(stack)
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "VersioningConfiguration": {"Status": "Enabled"},
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        },
    )


def test_dag_bucket_enforces_ssl():
    app = core.App()
    stack = S3Stack(app, "S3Stack")
    template = assertions.Template.from_stack(stack)
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Effect": "Deny",
                                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                            }
                        )
                    ]
                )
            }
        },
    )
