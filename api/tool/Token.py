import time
import hmac
import hashlib
import base64
class Token:
    def __init__(self):
        self.status = ''
        # @author dong.sun
        # 生成token
        # @return String  生成的Token,过期时间为两天
    def generateToken(self,key,expire=172800):
        gt_str = str(time.time() + expire)
        gt_byte = gt_str.encode("utf-8")
        sha1_tshexstr = hmac.new(key.encode("utf-8"), gt_byte, "sha1").hexdigest()
        token = gt_str + ":" + sha1_tshexstr
        b64_token = base64.urlsafe_b64encode(token.encode("utf-8"))
        return b64_token.decode("utf-8")
        # @author dong.sun
        # 验证token
        # @return Boolean
    def verificationToken(self,key, token):
        token_str = base64.urlsafe_b64decode(token).decode("utf-8")
        token_list = token_str.split(":")
        if len(token_list) != 2:
            return False
        ts_str = token_list[0]
        if float(ts_str) < time.time():
            return False
        known_sha1_tsstr = token_list[1]
        sha1 = hmac.new(key.encode("utf-8"), ts_str.encode("utf-8"), "sha1")
        calc_sha1_tsstr = sha1.hexdigest()
        if calc_sha1_tsstr != known_sha1_tsstr:
            return False
        return True