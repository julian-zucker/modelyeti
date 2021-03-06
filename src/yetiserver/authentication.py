import re

import redis

from yetiserver import redis_keys


def auth_manager_from_redis_connection(redis_conn):
    return UserManager(UserDao(redis_conn))


class UserManager:
    """Authenticates users."""

    def __init__(self, dao):
        self.dao = dao

    def register_user(self, user_name: str, user_email: str, hashed_password: str):
        """Registers a user with the given username, email, and bcrypt-hashed password.
        :return: True if the user is created, false if they were nto
        :raises RegistrationError: if there was an error in registering the user.
        """
        if not _user_name_is_legal(user_name):
            raise ValueError(f"Illegal username '{user_name}'")

        try:
            return self.dao.add_user(user_name, user_email, hashed_password)
        except (ValueError, RegistrationError) as e:
            raise RegistrationError("Could not register user.", e)

    def check_credentials(self, user_name, hashed_password):
        """Checks the given credentials to see if the user and password match.

        :param user_name: the name of the user to check
        :param hashed_password: the hashed password the user is trying to use to login
        :return: boolean, whether the user has provided credentials they can use to login
        """
        # Must be 128 hex digits
        if not re.compile("[0-9a-f]{128}").fullmatch(hashed_password):
            raise ValueError("hashed password must be a hex digest of a sha3_512 hash")
        retrieved_hash = self.dao.retrieve_password_hash_for_user(user_name)
        return retrieved_hash == hashed_password.encode("utf8")

    def update_email(self, username, new_email):
        """Sets the user's email to the given string."""
        self.dao.update_user_email(username, new_email)

    def update_password(self, username, new_password):
        """Sets the user's password to the one given. """
        self.dao.update_password_hash_for_user(username, new_password)

    def delete_user(self, username):
        """Deletes the given user.
        :returns: truthy value if there was a user with the given name, falsy otherwise.
        """
        self.dao.delete_user(username)

    def user_info(self, user_name):
        return self.dao.user_info(user_name)


def _user_name_is_legal(user_name):
    return re.compile('[A-Za-z0-9_!@#$%^&*]+').fullmatch(user_name)


class RegistrationError(BaseException):
    """This error is raised if there is an error while trying to register a user."""
    pass


class UserNotFoundError(BaseException):
    """This error is raised if the user was supposed to be found."""
    pass


class UserDao:
    def __init__(self, redis_conn: redis.Redis):
        self.rconn = redis_conn

    def add_user(self, user_name, user_email, user_password_hash):
        """Registers the given user, with the given name, email, and password hash.
        :raise ValueError: if the username is taken
        :raise RegistrationError: if the user couldn't be registered.
        """
        try:
            if self.user_exists(user_name):
                raise ValueError("username is taken")

            (self.rconn
             .pipeline()
             .sadd(redis_keys.for_user_set(), user_name)
             .set(redis_keys.for_user_password_hash(user_name), user_password_hash)
             .set(redis_keys.for_user_email(user_name), user_email)
             .execute())
        except redis.RedisError as e:
            raise RegistrationError(f"Could not register user {user_name} with email {user_email}", e)

    def retrieve_password_hash_for_user(self, user_name):
        """Returns the password hash associated with the given user, if they exist, or returns None otherwise"""
        if self.user_exists(user_name):
            return self.rconn.get(redis_keys.for_user_password_hash(user_name))
        else:
            raise UserNotFoundError("Username is not found")

    def update_password_hash_for_user(self, user_name, new_password_hash):
        """Updates the password hash associated with the given user, if they exist, or returns None otherwise"""
        if self.user_exists(user_name):
            self.rconn.set(redis_keys.for_user_password_hash(user_name), new_password_hash)
        else:
            raise UserNotFoundError("Username is not found")

    def update_user_email(self, user_name, new_email):
        if self.user_exists(user_name):
            self.rconn.set(redis_keys.for_user_email(user_name), new_email)
        else:
            raise UserNotFoundError("Username is not found")

    def user_exists(self, user_name):
        """Does the given user already exist?"""
        return self.rconn.sismember(redis_keys.for_user_set(), user_name)

    def user_info(self, user_name):
        if self.user_exists(user_name):
            return {
                "username": user_name,
                "email": self.rconn.get(redis_keys.for_user_email(user_name)).decode("utf8")
            }
        else:
            return None

    def delete_user(self, user_name):
        return self.rconn.delete(redis_keys.for_user_information(user_name))
