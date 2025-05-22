import os
from dotenv import load_dotenv
from get_email_code import EmailVerificationHandler
import logging

def test_temp_mail():
    """测试临时邮箱方式"""
    handler = EmailVerificationHandler()
    print("\n=== 测试临时邮箱模式 ===")
    code = handler.get_verification_code()
    if code:
        print(f"成功获取验证码: {code}")
    else:
        print("未能获取验证码")

def test_email_server():
    """测试邮箱服务器方式（POP3/IMAP）"""
    handler = EmailVerificationHandler()
    protocol = os.getenv('IMAP_PROTOCOL', 'POP3')
    print(f"\n=== 测试 {protocol} 模式 ===")
    print(f"邮箱服务器: {os.getenv('IMAP_SERVER')}")
    print(f"邮箱账号: {os.getenv('IMAP_USER')}")
    code = handler.get_verification_code()
    if code:
        print(f"成功获取验证码: {code}")
    else:
        print("未能获取验证码")



def main():
    # 加载环境变量
    load_dotenv()
    
    
    try:
        # 根据配置决定测试哪种模式
        if os.getenv('TEMP_MAIL') != 'null':
            test_temp_mail()
        else:
            test_email_server()
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main() 