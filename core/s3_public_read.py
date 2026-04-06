"""S3 bucket policy + CORS for public read of gym image URLs (<img src=...>)."""

from __future__ import annotations

import json
from typing import Sequence

from django.conf import settings


def gym_images_bucket_policy_json(bucket_name: str) -> str:
    """Allow anonymous ``s3:GetObject`` on all objects in the bucket."""
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "GymImagesPublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
            }
        ],
    }
    return json.dumps(policy, indent=2)


def gym_images_bucket_cors_configuration(
    allowed_origins: Sequence[str],
) -> dict:
    """CORS for browser GET/HEAD (e.g. fetch/canvas). ``*`` if list empty."""
    origins = list(allowed_origins) if allowed_origins else ["*"]
    return {
        "CORSRules": [
            {
                "ID": "gym-images-read",
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "HEAD"],
                "AllowedOrigins": origins,
                "ExposeHeaders": ["ETag", "Content-Length", "Content-Type", "Content-Disposition"],
                "MaxAgeSeconds": 86400,
            }
        ]
    }


def cors_origins_from_settings() -> list[str]:
    return list(getattr(settings, "AWS_S3_GYM_IMAGES_CORS_ORIGINS", []) or [])
