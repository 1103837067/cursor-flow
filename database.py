from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Text, text, BigInteger, ForeignKey, create_engine as sync_create_engine
from contextlib import asynccontextmanager
import logging
import os
import sys
import platform
import time
import re
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 检查是否指定了环境变量文件路径
env_file = os.getenv("ENV_FILE")
if env_file and os.path.exists(env_file):
    load_dotenv(env_file)
    logging.info(f"从 {env_file} 加载环境变量")

# 获取数据库连接信息，首先检查DATABASE_URL
database_url = os.getenv("DATABASE_URL")

if not database_url:
    # 如果没有直接的DATABASE_URL，则从分开的环境变量构建
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "cursor_accounts")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    
    # 构建数据库URL，确保使用asyncpg作为异步驱动
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # 确保DATABASE_URL使用的是asyncpg驱动
    if "postgresql" in database_url and "asyncpg" not in database_url:
        DATABASE_URL = database_url.replace("postgresql", "postgresql+asyncpg")
    else:
        DATABASE_URL = database_url

# 处理URL中的sslmode参数，asyncpg不支持在URL中使用sslmode参数
if "sslmode=" in DATABASE_URL:
    # 从URL中移除sslmode参数
    DATABASE_URL = re.sub(r'\?sslmode=\w+', '', DATABASE_URL)

# 设置数据库schema
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

# 用于同步操作的数据库URL
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")

# 输出数据库连接信息（隐藏密码）
try:
    masked_url = DATABASE_URL
    if "@" in DATABASE_URL and ":" in DATABASE_URL.split("@")[0]:
        user_part = DATABASE_URL.split("@")[0]
        if ":" in user_part:
            password_part = user_part.split(":")[1]
            masked_url = DATABASE_URL.replace(password_part, "****")
except Exception as e:
    logging.error(f"处理数据库URL时出错: {str(e)}")

# 基础模型类
class Base(DeclarativeBase):
    pass


# 账号模型
class AccountModel(Base):
    __tablename__ = "accounts"
    email = Column(String, primary_key=True)
    user = Column(String, nullable=False)
    password = Column(String, nullable=True)
    token = Column(String, nullable=False)
    usage_limit = Column(Text, nullable=True)
    created_at = Column(Text, nullable=True)
    status = Column(String, default="active", nullable=False)
    id = Column(BigInteger, nullable=False, index=True)  # 添加毫秒时间戳列并创建索引


# 账号使用记录模型
class AccountUsageRecordModel(Base):
    __tablename__ = "account_usage_records"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    account_id = Column(BigInteger, nullable=False, index=True)  # 账号ID
    email = Column(String, nullable=False, index=True)  # 账号邮箱
    ip = Column(String, nullable=True)  # 使用者IP
    user_agent = Column(Text, nullable=True)  # 使用者UA
    created_at = Column(Text, nullable=False)  # 创建时间


def create_engine():
    """创建数据库引擎"""
    try:
        connect_args = {}
        # 如果是PostgreSQL并且需要SSL
        if "postgresql" in DATABASE_URL and os.getenv("DB_SSL", "").lower() in ["true", "1", "yes"]:
            connect_args["ssl"] = True
        
        # 只有SQLite使用check_same_thread参数
        if "sqlite" in DATABASE_URL:
            connect_args["check_same_thread"] = False
            
        # 直接使用配置好的数据库URL
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            connect_args=connect_args,
            future=True,
        )
        logging.info(f"数据库引擎创建成功")
        return engine
    except Exception as e:
        logging.error(f"创建数据库引擎失败: {str(e)}")
        raise


@asynccontextmanager
async def get_session() -> AsyncSession:
    """创建数据库会话的异步上下文管理器"""
    # 为每个请求创建新的引擎和会话
    engine = create_engine()
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, future=True
    )

    session = async_session()
    try:
        # 确保连接有效
        await session.execute(text("SELECT 1"))
        yield session
    except Exception as e:
        logging.error(f"数据库会话错误: {str(e)}")
        try:
            await session.rollback()
        except Exception as rollback_error:
            logging.error(f"回滚过程中出错: {str(rollback_error)}")
        raise
    finally:
        try:
            await session.close()
        except Exception as e:
            logging.error(f"关闭会话时出错: {str(e)}")
        try:
            await engine.dispose()
        except Exception as e:
            logging.error(f"释放引擎时出错: {str(e)}")


async def init_db():
    """初始化数据库表结构"""
    try:
        engine = create_engine()
        # 如果使用PostgreSQL，确保schema存在
        if "postgresql" in DATABASE_URL:
            # 使用同步引擎创建schema
            try:
                # 移除URL中的sslmode参数并处理SSL配置
                modified_sync_url = SYNC_DATABASE_URL
                if "sslmode=" in modified_sync_url:
                    modified_sync_url = re.sub(r'\?sslmode=\w+', '', modified_sync_url)
                
                connect_args = {}
                if os.getenv("DB_SSL", "").lower() in ["true", "1", "yes"]:
                    connect_args["sslmode"] = "require"
                
                sync_engine = sync_create_engine(
                    modified_sync_url,
                    isolation_level="AUTOCOMMIT",
                    connect_args=connect_args
                )
                with sync_engine.connect() as connection:
                    try:
                        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
                        logging.info(f"已确保Schema存在: {DB_SCHEMA}")
                    except Exception as e:
                        logging.error(f"创建Schema时出错: {str(e)}")
                    finally:
                        sync_engine.dispose()
            except Exception as schema_error:
                logging.error(f"创建Schema时出错: {str(schema_error)}")
                
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
        logging.info("数据库初始化成功")
    except Exception as e:
        logging.error(f"数据库初始化失败: {str(e)}")
        raise 