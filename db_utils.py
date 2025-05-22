import asyncio
import time
from datetime import datetime
import logging

try:
    from sqlalchemy import select
    from database import get_session, AccountModel
    DB_AVAILABLE = True
except ImportError as e:
    logging.error(f"数据库模块导入失败: {str(e)}")
    DB_AVAILABLE = False

class DbAccountSaver:
    """数据库账号保存工具类，用于保存账号信息到PostgreSQL数据库"""
    
    @staticmethod
    async def save_account_to_db(email, password, user, token, total_usage):
        """
        保存账号信息到数据库
        
        Args:
            email: 注册邮箱
            password: 密码
            user: 用户标识
            token: 访问令牌
            total_usage: 使用限制
            
        Returns:
            bool: 是否保存成功
        """
        # 如果数据库模块不可用，直接返回
        if not DB_AVAILABLE:
            logging.error("数据库模块不可用，无法保存账号信息")
            return False
            
        try:
            
            async with get_session() as session:
                # 检查账号是否已存在
                result = await session.execute(
                    select(AccountModel).where(AccountModel.email == email)
                )
                existing_account = result.scalar_one_or_none()

                if existing_account:
                    logging.info(f"更新现有账号信息 (ID: {existing_account.id})")
                    existing_account.token = token
                    existing_account.user = user
                    existing_account.password = password
                    existing_account.usage_limit = str(total_usage)
                    # 如果账号状态是删除，更新为活跃
                    if existing_account.status == "deleted":
                        existing_account.status = "active"
                else:
                    logging.info("创建新账号记录")
                    # 生成毫秒级时间戳作为id
                    timestamp_ms = int(time.time() * 1000)
                    account = AccountModel(
                        email=email,
                        password=password,
                        token=token,
                        user=user,
                        usage_limit=str(total_usage),
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                        status="active",  # 设置默认状态为活跃
                        id=timestamp_ms,  # 设置毫秒时间戳id
                    )
                    session.add(account)

                await session.commit()
                return True
                
        except Exception as e:
            logging.error(f"保存账号信息到数据库失败: {str(e)}")
            return False
    
    @staticmethod
    def save_account(email, password, user, token, total_usage):
        """
        同步方法，用于保存账号信息到数据库
        
        Args:
            email: 注册邮箱
            password: 密码
            user: 用户标识
            token: 访问令牌
            total_usage: 使用限制
            
        Returns:
            bool: 是否保存成功
        """
        # 如果数据库模块不可用，直接返回
        if not DB_AVAILABLE:
            logging.error("数据库模块不可用，无法保存账号信息")
            return False
            
        try:
            # 使用新事件循环运行异步操作
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(DbAccountSaver.save_account_to_db(
                email, password, user, token, total_usage
            ))
            loop.close()
            return result
        except Exception as e:
            logging.error(f"执行保存账号信息时出错: {str(e)}")
            return False 