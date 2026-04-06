"""
Apply S3 bucket policy so gym image URLs work in the browser (<img src="https://...">).

Requires IAM permissions: s3:PutBucketPolicy, s3:PutBucketCORS, and optionally
s3:PutPublicAccessBlock for --relax-public-access-block.

If AWS "Block all public access" is on at the bucket level, put_bucket_policy may fail
until you run with --relax-public-access-block (or change settings in S3 console).

Usage:
  python manage.py configure_s3_gym_bucket --dry-run
  python manage.py configure_s3_gym_bucket --relax-public-access-block
"""

import json

from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.s3_gym_images import gym_images_boto3_client, gym_s3_configured
from core.s3_public_read import (
    cors_origins_from_settings,
    gym_images_bucket_cors_configuration,
    gym_images_bucket_policy_json,
)


class Command(BaseCommand):
    help = "Set bucket policy (public read) and CORS for AWS_S3_GYM_IMAGES_BUCKET."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print policy and CORS JSON only; do not call AWS.",
        )
        parser.add_argument(
            "--skip-cors",
            action="store_true",
            help="Do not update CORS configuration.",
        )
        parser.add_argument(
            "--relax-public-access-block",
            action="store_true",
            help=(
                "Allow bucket policies that grant public read (sets BlockPublicPolicy and "
                "RestrictPublicBuckets to false; keeps ACL-based public blocked)."
            ),
        )

    def handle(self, *args, **options):
        if not gym_s3_configured():
            raise CommandError(
                "S3 is not configured. Set AWS_S3_GYM_IMAGES_BUCKET and credentials "
                "(AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY or S3_ACCESS_KEY / S3_SECRET_KEY)."
            )

        bucket = (settings.AWS_S3_GYM_IMAGES_BUCKET or "").strip()
        if not bucket:
            raise CommandError("AWS_S3_GYM_IMAGES_BUCKET is empty.")

        policy_str = gym_images_bucket_policy_json(bucket)
        origins = cors_origins_from_settings()
        cors_cfg = gym_images_bucket_cors_configuration(origins)

        self.stdout.write(self.style.NOTICE(f"Bucket: {bucket}"))
        self.stdout.write("Bucket policy (public GetObject on all keys):\n")
        self.stdout.write(policy_str)
        self.stdout.write("\nCORS configuration:\n")
        self.stdout.write(json.dumps(cors_cfg, indent=2))
        if origins:
            self.stdout.write(f"\nCORS AllowedOrigins from settings: {origins}")
        else:
            self.stdout.write("\nCORS AllowedOrigins: * (set AWS_S3_GYM_IMAGES_CORS_ORIGINS to restrict)")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("\nDry run — no changes applied."))
            return

        client = gym_images_boto3_client()

        if options["relax_public_access_block"]:
            try:
                client.put_public_access_block(
                    Bucket=bucket,
                    PublicAccessBlockConfiguration={
                        "BlockPublicAcls": True,
                        "IgnorePublicAcls": True,
                        "BlockPublicPolicy": False,
                        "RestrictPublicBuckets": False,
                    },
                )
                self.stdout.write(self.style.SUCCESS("Updated public access block (policy-based public read allowed)."))
            except ClientError as e:
                raise CommandError(f"put_public_access_block failed: {e}") from e

        try:
            client.put_bucket_policy(
                Bucket=bucket,
                Policy=json.dumps(json.loads(policy_str), separators=(",", ":")),
            )
            self.stdout.write(self.style.SUCCESS("Bucket policy applied."))
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            hint = ""
            if code in ("AccessDenied", "403"):
                hint = " Check IAM for s3:PutBucketPolicy and bucket ownership."
            if "BlockPublicPolicy" in str(e) or code == "InvalidBucketState":
                hint += " Try again with --relax-public-access-block or disable Block Public Access in the S3 console."
            raise CommandError(f"put_bucket_policy failed: {e}{hint}") from e

        if not options["skip_cors"]:
            try:
                client.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_cfg)
                self.stdout.write(self.style.SUCCESS("CORS configuration applied."))
            except ClientError as e:
                raise CommandError(f"put_bucket_cors failed: {e}") from e

        self.stdout.write(
            self.style.SUCCESS(
                "\nDone. Image URLs returned by the API should load in <img> tags "
                "(use the bucket website-style URL or AWS_S3_GYM_IMAGES_URL_PREFIX)."
            )
        )
