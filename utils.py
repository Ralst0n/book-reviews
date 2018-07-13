from werkzeug.security import generate_password_hash, check_password_hash

def bad_cred(*credentials):
    """Returns true if a login credential is too short or username and password are the same"""
    for cred in credentials: 
        if cred is None or len(cred) < 4:
            return True
    cred_set = set(credentials)
    # if password/username are the same this will be true and we throw an error, otherwise credentials pass the last check
    return len(credentials) > len(cred_set)

def set_password(password):
    """Returns salted and hashed password for database"""
    return generate_password_hash(password)

def check_password(hashed, password):
    return check_password_hash(hashed, password)