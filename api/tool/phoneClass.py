import zhenzismsclient as smsclient
import random
class SendPhone:
    def __init__(self,phone):
        self.phone = phone
        self.client = smsclient.ZhenziSmsClient('https://sms_developer.zhenzikj.com',104480,'7b6cc136-8783-4442-a541-737f9b04cfb9')
    def sendLogin(self):
        # client = smsclient.ZhenziSmsClient('https://sms_developer.zhenzikj.com',104480,'7b6cc136-8783-4442-a541-737f9b04cfb9')
        code=''
        for num in range(1,5):
            code = code + str(random.randint(0,9))
        ids = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        messageId = ''
        for i in range(10):
            messageId += random.choice(ids)
        params = {
            'message':'您的验证码为:'+code+'验证码有效时间为5分钟，请勿向他人泄露。您正在登陆遇见你，如非本人操作，可忽略本消息',
            'number':self.phone,
            'messageId':messageId
            }
        result = self.client.send(params)
        return {
            "messageCode":code,
            "messageId":messageId,
            "result":result
        }
    def getMessage(self,Mid):
        return self.client.findSmsByMessageId('%s'%Mid)

# sends = SendPhone('111')
# print(sends.send())