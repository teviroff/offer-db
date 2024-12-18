from typing import Any, Callable, Self, Optional
from datetime import datetime, UTC
from ipaddress import IPv4Address

from sqlalchemy.dialects.postgresql import INET, TIMESTAMP
from minio import Minio

from ..utils import *
from .base import *
from .auxillary.address import *
from .. import serializers as ser


class PersonalAPIKey(Base):
    __tablename__ = 'personal_api_key'

    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), primary_key=True)
    ip: Mapped[IPv4Address] = mapped_column(INET, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    expiry_date: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    user: Mapped['User'] = relationship(back_populates='personal_api_keys')

    @classmethod
    def generate_key(cls, session: Session, user_id: int, ip: IPv4Address) -> str:
        from hashlib import sha256

        while True:
            key = sha256(f'{user_id}/{ip}/{datetime.now()}'.encode()).hexdigest()[:64]
            if session.query(PersonalAPIKey).filter(PersonalAPIKey.key == key).first() is None:
                break
        return key

    def expire(self, session: Session) -> None:
        session.delete(self)

    @classmethod
    def generate(cls, session: Session, user: 'User', ip: IPv4Address, expiry_date: datetime) -> Self:
        if user.id is None:
            logger.error('\'PersonalAPIKey.generate\' called on user without id (user_email=\'%s\')', user.email)
            raise ValueError('Can\'t generate personal API key for user without id')
        api_key: PersonalAPIKey | None = session.get(PersonalAPIKey, (user.id, ip))
        if api_key is not None:
            api_key.expire(session)
        key = cls.generate_key(session, user.id, ip)
        api_key = PersonalAPIKey(ip=ip, key=key, expiry_date=expiry_date, user=user)
        session.add(api_key)
        return api_key

    @classmethod
    def get(cls, session: Session, key: str) -> Self | None:
        api_key: PersonalAPIKey | None = session.query(PersonalAPIKey).filter(PersonalAPIKey.key == key).first()
        if api_key is None:
            return
        if api_key.expiry_date <= datetime.now(UTC):
            session.delete(api_key)
            return
        return api_key

    def __str__(self):
        return f'personal-{self.key}'

    def __repr__(self):
        return self.__str__()


class DeveloperAPIKey(Base):
    __tablename__ = 'developer_api_key'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)

    @classmethod
    def generate_key(cls, session: Session) -> str:
        from hashlib import sha256

        while True:
            key = sha256(f'{datetime.now()}'.encode()).hexdigest()[:64]
            if session.query(DeveloperAPIKey).filter(DeveloperAPIKey.key == key).first() is None:
                break
        return key

    @classmethod
    def generate(cls, session: Session) -> Self:
        key = cls.generate_key(session)
        api_key = DeveloperAPIKey(key=key)
        session.add(api_key)
        return api_key

    @classmethod
    def get(cls, session: Session, key: str) -> Self | None:
        return session.query(DeveloperAPIKey).filter(DeveloperAPIKey.key == key).first()

    def __str__(self):
        return f'dev-{self.key}'

    def __repr__(self):
        return self.__str__()


class APIKey:
    """Helper class, that encapsulates getter methods of all key types."""

    KeysUnion = PersonalAPIKey | DeveloperAPIKey

    class Type(IntEnum):
        Personal = 0
        Developer = 1

    key_type_str_to_enum: dict[str, Type] = {
        'personal': Type.Personal,
        'dev': Type.Developer,
    }

    @classmethod
    def deserialize(cls, api_key: ser.APIKey) -> tuple[Type, str]:
        type, key = api_key.split(sep='-', maxsplit=1)
        return cls.key_type_str_to_enum[type], key

    key_type_to_handler: dict[Type, Callable[[Session, str], KeysUnion | None]] = {
        Type.Personal: PersonalAPIKey.get,
        Type.Developer: DeveloperAPIKey.get,
    }

    @classmethod
    def get(cls, session: Session, api_key: ser.APIKey) -> KeysUnion | None:
        type, key = APIKey.deserialize(api_key)
        return cls.key_type_to_handler[type](session, key)


class CreateUserErrorCode(IntEnum):
    NON_UNIQUE_EMAIL = 0

# TODO: change password method
class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))

    personal_api_keys: Mapped[list['PersonalAPIKey']] = \
        relationship(back_populates='user', cascade='all, delete-orphan')
    user_info: Mapped['UserInfo'] = relationship(back_populates='user', cascade='all, delete-orphan')
    responses: Mapped[set['OpportunityResponse']] = \
        relationship(back_populates='user', cascade='all, delete-orphan')

    @classmethod
    def hash_password(cls, password: str) -> str:
        from hashlib import sha256

        return sha256(password.encode()).hexdigest()

    @classmethod
    def create(cls, session: Session, credentials: ser.User.Credentials) -> Self | GenericError[CreateUserErrorCode]:
        user = session.query(User).filter(User.email == credentials.email).first()
        if user is not None:
            logger.debug('\'User.create\' exited with \'NON_UNIQUE_EMAIL\' error (email=\'%s\')', credentials.email)
            return GenericError(error_code=CreateUserErrorCode.NON_UNIQUE_EMAIL,
                                error_message='User with given email already exists')
        user = User(email=credentials.email, password_hash=cls.hash_password(credentials.password))
        user.user_info = UserInfo(user=user)
        session.add(user)
        return user

    @classmethod
    def login(cls, session: Session, credentials: ser.User.Credentials) -> Optional['User']:
        """Check given credentials and return User instance if given credentials are correct.
           Call to this function should be followed by creating a PersonalAPIKey instance."""

        user: User | None = session.query(User).filter(User.email == credentials.email).first()
        if user is None:
            logger.debug('\'User.login\' exited because user with given email doesn\'t exist '
                         '(email=\'%s\')', credentials.email)
            return None
        if user.password_hash != cls.hash_password(credentials.password):
            logger.debug('\'User.login\' exited because user with given email have different password '
                         '(email=\'%s\')', credentials.email)
            return None
        return user


class UserAvatarFormat(Enum):
    PNG = ('png', 'image/png')

# TODO: store address
class UserInfo(Base):
    __tablename__ = 'user_info'

    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'), primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=True, default=None)
    surname: Mapped[str] = mapped_column(String(40), nullable=True, default=None)
    birthday: Mapped[datetime] = mapped_column(nullable=True, default=None)
    avatar_format: Mapped[UserAvatarFormat | None] = mapped_column(nullable=True, default=None)

    user: Mapped['User'] = relationship(back_populates='user_info')
    # phone_number: Mapped[Optional['PhoneNumber']] = \
    #     relationship(back_populates='user_info', cascade='all, delete-orphan')
    cvs: Mapped[list['CV']] = relationship(back_populates='user_info', cascade='all, delete-orphan')
    # files: Mapped[list['File']] = relationship(back_populates='user_info', cascade='all, delete-orphan')

    @property
    def fullname(self) -> str:
        return f'{self.name} {self.surname}'

    @property
    def avatar_url(self) -> str:
        return f'/api/user/avatar?user_id={self.user_id}'

    def update_name(self, new_name: ser.UserInfo.Name) -> None:
        self.name = new_name

    def update_surname(self, new_surname: ser.UserInfo.Surname) -> None:
        self.surname = new_surname

    def update_birthday(self, new_birthday: ser.Date) -> None:
        self.birthday = datetime(new_birthday.year, new_birthday.month, new_birthday.day)

    update_field_handlers: list[tuple[str, Callable[[Self, Any], None]]] = [
        ('name', update_name),
        ('surname', update_surname),
        ('birthday', update_birthday),
    ]

    def update(self, fields: ser.UserInfo.Update) -> None:
        """Method, that encapsulates logic for updates of all fields."""

        for field, handler in UserInfo.update_field_handlers:
            if getattr(fields, field) is None:
                continue
            handler(self, getattr(fields, field))

    def update_avatar(self, minio_client: Minio, file: FileStream[UserAvatarFormat]) -> None:
        self.avatar_format = file.format
        minio_client.put_object(
            'user-avatar', f'{self.user_id}.{file.format.value[0]}', file.stream, 
            file.size if file.size else -1, part_size=(5 * 1024 * 1024)
        )

    def get_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'surname': self.surname,
            'birthday': self.birthday.strftime('%Y-%m-%d') if self.birthday is not None else None,
            # TODO: city, phone number
        }

    def get_avatar(self, minio_client: Minio) -> bytes:
        filename = f'{self.user_id}.{self.avatar_format.value[0]}' if self.avatar_format is not None \
            else 'default.png'
        response = None
        try:
            response = minio_client.get_object('user-avatar', filename)
            avatar = response.read()
        finally:
            if response is not None:
                response.close()
                response.release_conn()
        return avatar

    def get_cvs(self) -> dict[str, str]:
        return {str(cv.id): cv.name for cv in self.cvs}


# class PhoneNumber(Base):
#     __tablename__ = 'phone_number'

#     user_info_id: Mapped[int] = mapped_column(ForeignKey('user_info.user_id'), primary_key=True)
#     country_id: Mapped[int] = mapped_column(ForeignKey('country.id'))
#     subscriber_number: Mapped[str] = mapped_column(String(12))

#     user_info: Mapped['UserInfo'] = relationship(back_populates='phone_number')
#     country: Mapped['Country'] = relationship()

#     @classmethod
#     def update(
#         cls, session: Session,
#         user: 'User',
#         country: 'Country',
#         subscriber_number: ser.auxillary.PhoneNumber.SubscriberNumber,
#     ) -> Self:
#         if (self := user.user_info.phone_number) is None:
#             self = PhoneNumber(user_info=user.user_info, country=country, subscriber_number=subscriber_number)
#             session.add(self)
#         else:
#             self.country = country
#             self.subscriber_number = subscriber_number
#         return self


class CVFormat(Enum):
    PDF = ('pdf', 'application/pdf')

# TODO: CV sharing & updating file of an existing CV
class CV(Base):
    __tablename__ = 'cv'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_info_id: Mapped[int] = mapped_column(ForeignKey('user_info.user_id'))
    name: Mapped[str] = mapped_column(String(50))
    format: Mapped[CVFormat]
    public: Mapped[bool] = mapped_column(default=False)

    user_info: Mapped['UserInfo'] = relationship(back_populates='cvs')

    @classmethod
    def add(cls, session: Session, minio_client: Minio, user: User,
            file: FileStream[CVFormat], name: ser.CV.Name) -> Self:
        cv = CV(user_info=user.user_info, name=name, format=file.format)
        session.add(cv)
        session.flush([cv])
        minio_client.put_object('user-cv', f'{cv.id}.{file.format.value[0]}', file.stream, file.size)
        return cv

    def rename(self, name: ser.CV.Name) -> None:
        self.name = name

    def delete(self, session: Session, minio_client: Minio) -> None:
        minio_client.remove_object('user-cv', f'{self.id}.{self.format.value[0]}')
        session.delete(self)


# class FileFormat(Enum):
#     PDF = ('pdf', 'application/pdf')

# class File(Base):
#     __tablename__ = 'file'

#     id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
#     user_info_id: Mapped[int] = mapped_column(ForeignKey('user_info.user_id'))
#     format: Mapped[FileFormat]

#     user_info: Mapped['UserInfo'] = relationship(back_populates='files')


# magic fix, placing it in the beggining of a file results in error
from ..models.opportunity import OpportunityResponse
