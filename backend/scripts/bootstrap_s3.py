#!/usr/bin/env python3
"""
S3 Bucket Bootstrap Script
Creates and configures S3 bucket for SBH file storage
"""
import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def bootstrap_s3_bucket(bucket_name, region='us-east-1'):
    """Create and configure S3 bucket for SBH"""
    try:
        # Create S3 client
        s3_client = boto3.client('s3', region_name=region)
        
        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' already exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                print(f"Creating bucket '{bucket_name}' in region '{region}'...")
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region} if region != 'us-east-1' else {}
                )
                print(f"✅ Bucket '{bucket_name}' created successfully")
            else:
                print(f"❌ Error checking bucket: {e}")
                return False
        
        # Configure bucket for SBH
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "SBHFileStorage",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::*:role/aws-elasticbeanstalk-ec2-role"
                    },
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:DeleteObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/stores/*"
                    ]
                }
            ]
        }
        
        # Apply bucket policy
        try:
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=str(bucket_policy).replace("'", '"')
            )
            print(f"✅ Bucket policy applied")
        except ClientError as e:
            print(f"⚠️  Warning: Could not apply bucket policy: {e}")
        
        # Enable CORS for web access
        cors_configuration = {
            'CORSRules': [{
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE'],
                'AllowedOrigins': ['*'],
                'ExposeHeaders': ['ETag']
            }]
        }
        
        try:
            s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_configuration
            )
            print(f"✅ CORS configuration applied")
        except ClientError as e:
            print(f"⚠️  Warning: Could not apply CORS configuration: {e}")
        
        print(f"\n🎉 S3 bucket '{bucket_name}' is ready for SBH!")
        print(f"   ARN: arn:aws:s3:::{bucket_name}")
        print(f"   Region: {region}")
        print(f"\nNext steps:")
        print(f"1. Set S3_BUCKET_NAME={bucket_name} in your environment")
        print(f"2. Ensure AWS credentials are configured")
        print(f"3. Deploy SBH with STORAGE_PROVIDER=s3")
        
        return True
        
    except NoCredentialsError:
        print("❌ AWS credentials not found. Please configure AWS CLI or set environment variables.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function"""
    # Check for help
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print("Usage: python bootstrap_s3.py <bucket-name> [region]")
        print("Example: python bootstrap_s3.py sbh-files-us-east-1 us-east-1")
        sys.exit(0)
    
    if len(sys.argv) < 2:
        print("Usage: python bootstrap_s3.py <bucket-name> [region]")
        print("Example: python bootstrap_s3.py sbh-files-us-east-1 us-east-1")
        sys.exit(1)
    
    bucket_name = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else 'us-east-1'
    
    print(f"🚀 Bootstrapping S3 bucket for SBH...")
    print(f"   Bucket: {bucket_name}")
    print(f"   Region: {region}")
    print()
    
    success = bootstrap_s3_bucket(bucket_name, region)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
