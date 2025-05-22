print("开始测试导入")

print("尝试导入logging")
import logging
print("导入logging成功")

print("尝试导入database模块")
try:
    import database
    print("导入database成功")
except Exception as e:
    print(f"导入database失败: {e}")
    
print("尝试导入AccountModel")
try:
    from database import AccountModel
    print("导入AccountModel成功")
except Exception as e:
    print(f"导入AccountModel失败: {e}")

print("尝试导入db_utils模块")
try:
    import db_utils
    print("导入db_utils成功")
except Exception as e:
    print(f"导入db_utils失败: {e}")

print("尝试导入DbAccountSaver")
try:
    from db_utils import DbAccountSaver
    print("导入DbAccountSaver成功")
except Exception as e:
    print(f"导入DbAccountSaver失败: {e}")

print("导入测试完成") 