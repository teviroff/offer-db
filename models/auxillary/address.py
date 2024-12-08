from typing import Self

from ...utils import *
from ...models.base import *
from ... import serializers as ser


class CreateCountryErrorCode(IntEnum):
    NON_UNIQUE_NAME = 0

class Country(Base):
    __tablename__ = 'country'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    phone_code: Mapped[str] = mapped_column(String(3))

    cities: Mapped[list['City']] = relationship(back_populates='country')

    @classmethod
    def create(cls, session: Session, fields: ser.Country) -> Self | GenericError[CreateCountryErrorCode]:
        country = session.query(Country).filter(Country.name == fields.name).first()
        if country is not None:
            logger.debug('\'Country.create\' exited with \'NON_UNIQUE_NAME\' error (name=\'%s\')', fields.name)
            return GenericError(
                error_code=CreateCountryErrorCode.NON_UNIQUE_NAME,
                error_message='Country with given name already exists'
            )
        country = Country(name=fields.name, phone_code=fields.phone_code)
        session.add(country)
        return country


class City(Base):
    __tablename__ = 'city'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    country_id: Mapped[int] = mapped_column(ForeignKey('country.id'))
    name: Mapped[str] = mapped_column(String(50))

    country: Mapped['Country'] = relationship(back_populates='cities')

    @classmethod
    def create(cls, session: Session, country: Country, fields: ser.City) -> Self:
        city = City(country=country, name=fields.name)
        session.add(city)
        return city

    @property
    def full(self) -> str:
        return f'{self.country.name}, {self.name}'
