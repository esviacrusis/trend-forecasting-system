
################################################################################################
# Module    :   Check AWS S3 database connection
# Author    :   Eric S. Viacrusis
# Date      :   April 1, 2026
#
# UPDATES
# April 1   :   create S3Client class to handle AWS S3 operations (upload, download, list files)
################################################################################################


import boto3


class S3Client:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3 = None

        try:
            self.s3 = boto3.client("s3")
            print("✅ S3 client initialized")

        except Exception as e:
            print(f"❌ Failed to initialize S3 client: {e}")

        finally:
            # Nothing to close for boto3, but useful for logging/debugging
            print("ℹ️ S3Client init process completed")

    def upload_file(self, local_path: str, s3_key: str):
        try:
            if self.s3 is None:
                raise Exception("S3 client not initialized")

            self.s3.upload_file(local_path, self.bucket_name, s3_key)

            print(f"✅ Uploaded: {local_path} → s3://{self.bucket_name}/{s3_key}")

        except Exception as e:
            print(f"❌ Upload failed: {e}")

        finally:
            print("ℹ️ upload_file() execution finished")

    def download_file(self, s3_key: str, local_path: str):
        try:
            if self.s3 is None:
                raise Exception("S3 client not initialized")

            self.s3.download_file(self.bucket_name, s3_key, local_path)

            print(f"✅ Downloaded: s3://{self.bucket_name}/{s3_key} → {local_path}")

        except Exception as e:
            print(f"❌ Download failed: {e}")

        finally:
            print("ℹ️ download_file() execution finished")

    def list_files(self, prefix: str):
        try:
            if self.s3 is None:
                raise Exception("S3 client not initialized")

            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if "Contents" in response:
                print("📂 Files found:")
                for obj in response["Contents"]:
                    print(obj["Key"])
            else:
                print("⚠️ No files found.")

        except Exception as e:
            print(f"❌ List operation failed: {e}")

        finally:
            print("ℹ️ list_files() execution finished")