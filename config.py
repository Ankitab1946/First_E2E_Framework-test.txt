# from functools import lru_cache
# from sqlalchemy.engine import URL
# from pydantic_settings import BaseSettings


# class Settings(BaseSettings):
#     app_name: str = "Data Dictionary Streamlit Admin"
#     app_env: str = "LOCAL"
#     app_debug: bool = False

#     # SQL Server configuration.
#     # For Windows Authentication, set SQLSERVER_WINDOWS_AUTH=true.
#     sqlserver_server: str = "localhost"
#     sqlserver_database: str = "PRJ_DB"
#     sqlserver_windows_auth: bool = True
#     sqlserver_user: str = ""
#     sqlserver_password: str = ""
#     sqlserver_driver: str = "ODBC Driver 17 for SQL Server"
#     sqlserver_trust_cert: str = "yes"

#     # Supported runtime environments shown in the Streamlit side panel.
#     app_environments: str = "LOCAL,DEV,UAT,PROD"
#     selected_environment: str = "LOCAL"

#     # Role/security configuration.
#     admin_users: str = "*,sysuser"
#     default_user: str = "sysuser"
#     local_auto_admin: bool = True

#     # Excel and DB switches.
#     excel_template_version: str = "1.0"
#     max_upload_size_mb: int = 20
#     enable_db: bool = False

#     # S3/S3-compatible object storage export configuration.
#     # Supports AWS S3 and internal S3-compatible endpoints such as MinIO/Ceph.
#     s3_bucket_name: str = ""
#     s3_prefix: str = "data-dictionary"
#     aws_region: str = "ap-south-1"
#     s3_secure: bool = True
#     s3_host: str = ""
#     s3_secure_host: str = ""
#     s3_port: str = ""
#     s3_endpoint_url: str = ""
#     s3_use_ssl: bool = False
#     s3_verify_ssl: bool = False
#     aws_access_key_id: str = ""
#     aws_secret_access_key: str = ""

#     @property
#     def database_url(self):
#         query = {
#             "driver": self.sqlserver_driver,
#             "TrustServerCertificate": self.sqlserver_trust_cert,
#         }

#         if self.sqlserver_windows_auth:
#             query["Trusted_Connection"] = "yes"
#             return URL.create(
#                 "mssql+pyodbc",
#                 host=self.sqlserver_server,
#                 database=self.sqlserver_database,
#                 query=query,
#             )

#         return URL.create(
#             "mssql+pyodbc",
#             username=self.sqlserver_user,
#             password=self.sqlserver_password,
#             host=self.sqlserver_server,
#             database=self.sqlserver_database,
#             query=query,
#         )

#     @property
#     def environment_names(self) -> list[str]:
#         return [item.strip().upper() for item in self.app_environments.split(",") if item.strip()]

#     @property
#     def admin_user_list(self) -> list[str]:
#         return [item.strip().lower() for item in self.admin_users.split(",") if item.strip()]

#     class Config:
#         env_file = ".env"
#         extra = "ignore"


# @lru_cache
# def get_settings() -> Settings:
#     return Settings()


from functools import lru_cache
from sqlalchemy.engine import URL
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Data Dictionary Streamlit Admin"
    app_env: str = "LOCAL"
    app_debug: bool = False

    # SQL Server configuration.
    # For Windows Authentication, set SQLSERVER_WINDOWS_AUTH=true.
    sqlserver_server: str = "localhost"
    sqlserver_database: str = "PRJ_DB"
    sqlserver_windows_auth: bool = True
    sqlserver_user: str = ""
    sqlserver_password: str = ""
    sqlserver_driver: str = "ODBC Driver 17 for SQL Server"
    sqlserver_trust_cert: str = "yes"

    # Supported runtime environments shown in the Streamlit side panel.
    app_environments: str = "LOCAL,DEV,UAT,PROD"
    selected_environment: str = "LOCAL"

    # Role/security configuration.
    admin_users: str = "*,sysuser"
    default_user: str = "sysuser"
    local_auto_admin: bool = True

    # Excel and DB switches.
    excel_template_version: str = "1.0"
    max_upload_size_mb: int = 20
    enable_db: bool = False

    # S3/S3-compatible object storage export configuration.
    # Supports AWS S3 and internal S3-compatible endpoints such as MinIO/Ceph.
    # Both S3_* / AWS_* names and simple internal names are supported.
    s3_bucket_name: str = ""
    s3_prefix: str = "data-dictionary"
    aws_region: str = "ap-south-1"
    s3_secure: bool = False
    s3_host: str = ""
    s3_secure_host: str = ""
    s3_port: str = ""
    s3_endpoint_url: str = ""
    s3_use_ssl: bool = False
    s3_verify_ssl: bool = False
    s3_addressing_style: str = "path"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Alternative/simple names commonly used in internal scripts.
    bucket_name: str = ""
    host: str = ""
    secure_host: str = ""
    access_key_id: str = ""
    secret_key: str = ""

    @property
    def effective_s3_bucket_name(self) -> str:
        return self.s3_bucket_name or self.bucket_name

    @property
    def effective_s3_host(self) -> str:
        return self.s3_host or self.host

    @property
    def effective_s3_secure_host(self) -> str:
        return self.s3_secure_host or self.secure_host

    @property
    def effective_aws_access_key_id(self) -> str:
        return self.aws_access_key_id or self.access_key_id

    @property
    def effective_aws_secret_access_key(self) -> str:
        return self.aws_secret_access_key or self.secret_key

    @property
    def database_url(self):
        query = {
            "driver": self.sqlserver_driver,
            "TrustServerCertificate": self.sqlserver_trust_cert,
        }

        if self.sqlserver_windows_auth:
            query["Trusted_Connection"] = "yes"
            return URL.create(
                "mssql+pyodbc",
                host=self.sqlserver_server,
                database=self.sqlserver_database,
                query=query,
            )

        return URL.create(
            "mssql+pyodbc",
            username=self.sqlserver_user,
            password=self.sqlserver_password,
            host=self.sqlserver_server,
            database=self.sqlserver_database,
            query=query,
        )

    @property
    def environment_names(self) -> list[str]:
        return [item.strip().upper() for item in self.app_environments.split(",") if item.strip()]

    @property
    def admin_user_list(self) -> list[str]:
        return [item.strip().lower() for item in self.admin_users.split(",") if item.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
