from werkzeug.security import generate_password_hash, check_password_hash

class Password(object):
    def __init__(self, password):
        self.set_password(password)
    
    def set_password(self, password):
        self.secret_password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.secret_password, password)
