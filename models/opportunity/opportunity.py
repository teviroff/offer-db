from typing import Any, Self, Iterable, Optional

from minio import Minio
from sqlalchemy import select, func

from ...utils import *
from ..base import *
from ... import serializers as ser

from ..auxillary.address import City
from .. import user as _user
from . import form as _form


class OpportunityDescriptionFormat(Enum):
    MARKDOWN = ('md', 'text/markdown')

class Opportunity(Base):
    __tablename__ = 'opportunity'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    link: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey('opportunity_provider.id'))
    has_description: Mapped[bool] = mapped_column(default=False)
    has_form: Mapped[bool] = mapped_column(default=False)

    provider: Mapped['OpportunityProvider'] = relationship(back_populates='opportunities')
    tags: Mapped[set['OpportunityTag']] = relationship(secondary='opportunity_to_tag', back_populates='opportunities')
    geotags: Mapped[set['OpportunityGeotag']] = relationship(secondary='opportunity_to_geotag',
                                                              back_populates='opportunities')
    cards: Mapped[list['OpportunityCard']] = relationship(back_populates='opportunity', cascade='all, delete-orphan')
    responses: Mapped[list['OpportunityResponse']] = relationship(back_populates='opportunity',
                                                                  cascade='all, delete-orphan')

    @property
    def description_url(self) -> str:
        return f'/api/opportunity/description?opportunity_id={self.id}'

    @property
    def form_url(self) -> str:
        return f'/api/opportunity/form?opportunity_id={self.id}'

    @classmethod
    def create(cls, session: Session, provider: 'OpportunityProvider', fields: ser.Opportunity.Create) -> Self:
        opportunity = Opportunity(name=fields.name, link=str(fields.link), provider=provider)
        session.add(opportunity)
        return opportunity

    def get_form(self) -> Optional['_form.OpportunityForm']:
        if not self.has_form:
            return None
        return _form.OpportunityForm.objects(id=self.id).first()

    @staticmethod
    def apply_filters_to_statement[S](
        statement: S,
        *, providers: Iterable['OpportunityProvider'],
        tags: Iterable['OpportunityTag'],
        geotags: Iterable['OpportunityGeotag'],
        user: Optional['_user.User'] = None,
        public: bool = True,
    ):
        if len(providers) > 0:
            statement = statement.where(Opportunity.provider_id.in_(provider.id for provider in providers))
        if len(tags) > 0:
            substatement = select(OpportunityToTag.opportunity_id) \
                .where(OpportunityToTag.tag_id.in_(tag.id for tag in tags)) \
                .group_by(OpportunityToTag.opportunity_id) \
                .having(func.count(OpportunityToTag.tag_id) == len(tags))
            statement = statement.where(Opportunity.id.in_(substatement))
        if len(geotags) > 0:
            substatement = select(OpportunityToGeotag.opportunity_id) \
                .where(OpportunityToGeotag.geotag_id.in_(geo_tag.id for geo_tag in geotags)) \
                .group_by(OpportunityToGeotag.opportunity_id) \
                .having(func.count(OpportunityToGeotag.geotag_id) > 0)
            statement = statement.where(Opportunity.id.in_(substatement))
        if user is not None:
            statement = statement.where(Opportunity.id.in_(response.opportunity_id for response in user.responses))
        if public:
            statement = statement.where(Opportunity.cards.any())
        return statement

    # The maximum amount of opportunities returned from database in one query
    PAGE_SIZE: int = 12 

    @classmethod
    def filter_pages(
        cls, session: Session,
        *, providers: Iterable['OpportunityProvider'],
        tags: Iterable['OpportunityTag'],
        geotags: Iterable['OpportunityGeotag'],
        user: Optional['_user.User'] = None,
        public: bool = True,
    ) -> int:
        statement = cls.apply_filters_to_statement(select(func.count()).select_from(Opportunity),
                                                   providers=providers, tags=tags, geotags=geotags,
                                                   user=user, public=public)
        count: int = session.execute(statement).scalars().first()
        return (count + cls.PAGE_SIZE - 1) // cls.PAGE_SIZE

    @classmethod
    def filter(
        cls, session: Session,
        *, providers: Iterable['OpportunityProvider'],
        tags: Iterable['OpportunityTag'],
        geotags: Iterable['OpportunityGeotag'],
        page: int,
        user: Optional['_user.User'] = None,
        public: bool = True,
    ) -> list['Opportunity']:
        statement = (
            cls.apply_filters_to_statement(select(Opportunity), providers=providers, tags=tags,
                                           geotags=geotags, user=user, public=public)
                .offset((page - 1) * cls.PAGE_SIZE)
                .limit(cls.PAGE_SIZE)
        )
        return session.execute(statement).scalars().all()

    def add_tags(self, tags: Iterable['OpportunityTag']) -> None:
        for tag in tags:
            self.tags.add(tag)

    def add_geotags(self, geo_tags: Iterable['OpportunityGeotag']) -> None:
        for geo_tag in geo_tags:
            self.geotags.add(geo_tag)

    def update_description(self, minio_client: Minio, file: FileStream[OpportunityDescriptionFormat]) -> None:
        self.has_description = True
        minio_client.put_object('opportunity-description', f'{self.id}.md', file.stream, file.size)

    def get_tags(self) -> dict[str, str]:
        return {tag.id: tag.name for tag in self.tags}

    def get_geotags(self) -> dict[str, str]:
        return {geotag.id: geotag.city.name for geotag in self.geotags}

    def get_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'link': self.link,
            'provider_id': self.provider_id,
            'provider_logo_url': self.provider.logo_url,
            'provider_name': self.provider.name,
            'tags': self.get_tags(),
            'geotags': self.get_geotags(),
        }

    def get_description(self, minio_client: Minio) -> bytes:
        filename = f'{self.id}.md' if self.has_description else 'default.md'
        response = None
        try:
            response = minio_client.get_object('opportunity-description', filename)
            description = response.read()
        finally:
            response.close()
            response.release_conn()
        return description


class ProviderLogoFormat(Enum):
    PNG = ('png', 'image/png')

# TODO: update logo method
class OpportunityProvider(Base):
    __tablename__ = 'opportunity_provider'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    logo_format: Mapped[ProviderLogoFormat | None] = mapped_column(nullable=True, default=None)

    opportunities: Mapped[list['Opportunity']] = relationship(back_populates='provider', cascade='all, delete-orphan')

    @property
    def logo_url(self) -> str:
        return f'/api/opportunity-provider/logo/{self.id}'

    @classmethod
    def create(cls, session: Session, fields: ser.OpportunityProvider.Create) -> Self:
        provider = OpportunityProvider(name=fields.name)
        session.add(provider)
        return provider

    def get_logo(self, minio_client: Minio) -> bytes:
        filename = f'{self.id}.{self.logo_format}' if self.logo_format is not None \
            else 'default.png'
        response = None
        try:
            response = minio_client.get_object('opportunity-provider-logo', filename)
            avatar = response.read()
        finally:
            if response is not None:
                response.close()
                response.release_conn()
        return avatar

    @classmethod
    def get_all(cls, session: Session) -> dict[str, str]:
        return {str(provider.id): provider.name for provider in session.query(OpportunityProvider).all()}


class CreateOpportunityTagErrorCode(IntEnum):
    NON_UNIQUE_NAME = 0

class OpportunityTag(Base):
    __tablename__ = 'opportunity_tag'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    opportunities: Mapped[list['Opportunity']] = relationship(secondary='opportunity_to_tag', back_populates='tags')

    @classmethod
    def create(cls, session: Session, fields: ser.OpportunityTag.Create) \
            -> Self | GenericError[CreateOpportunityTagErrorCode]:
        tag = session.query(OpportunityTag).filter(OpportunityTag.name == fields.name).first()
        if tag is not None:
            logger.debug('\'OpportunityTag.create\' exited with \'NON_UNIQUE_NAME\' error (name=\'%s\')', fields.name)
            return GenericError(
                error_code=CreateOpportunityTagErrorCode.NON_UNIQUE_NAME,
                error_message='Tag with given name already exists',
            )
        tag = OpportunityTag(name=fields.name)
        session.add(tag)
        return tag

    @classmethod
    def get_all(cls, session: Session) -> dict[str, str]:
        return {str(tag.id): tag.name for tag in session.query(OpportunityTag).all()}


class CreateOpportunityGeotagErrorCode(IntEnum):
    NON_UNIQUE_CITY = 0

class OpportunityGeotag(Base):
    __tablename__ = 'opportunity_geotag'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(ForeignKey('city.id'), unique=True)

    city: Mapped['City'] = relationship()
    opportunities: Mapped[list['Opportunity']] = relationship(secondary='opportunity_to_geotag',
                                                              back_populates='geotags')

    @classmethod
    def create(cls, session: Session, city: City) -> Self | GenericError[CreateOpportunityGeotagErrorCode]:
        geotag = session.query(OpportunityGeotag).filter(OpportunityGeotag.city == city).first()
        if geotag is not None:
            logger.debug('\'OpportunityGeoTag.create\' exited with \'NON_UNIQUE_CITY\' error (city_id=%i)', city.id)
            return GenericError(
                error_code=CreateOpportunityGeotagErrorCode.NON_UNIQUE_CITY,
                error_message='Geo tag for given city already exists',
            )
        geotag = OpportunityGeotag(city=city)
        session.add(geotag)
        return geotag

    @classmethod
    def get_all(cls, session: Session) -> dict[str, tuple[str, str]]:
        return {str(geotag.id): (geotag.city.country.name, geotag.city.name)
                for geotag in session.query(OpportunityGeotag).all()}


class OpportunityToTag(Base):
    __tablename__ = 'opportunity_to_tag'

    opportunity_id: Mapped[int] = mapped_column(ForeignKey('opportunity.id'), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey('opportunity_tag.id'), primary_key=True)


class OpportunityToGeotag(Base):
    __tablename__ = 'opportunity_to_geotag'

    opportunity_id: Mapped[int] = mapped_column(ForeignKey('opportunity.id'), primary_key=True)
    geotag_id: Mapped[int] = mapped_column(ForeignKey('opportunity_geotag.id'), primary_key=True)


class OpportunityCard(Base):
    __tablename__ = 'opportunity_card'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey('opportunity.id'))
    title: Mapped[str] = mapped_column(String(100))
    subtitle: Mapped[str | None] = mapped_column(String(50), nullable=True)

    opportunity: Mapped['Opportunity'] = relationship(back_populates='cards')

    @classmethod
    def create(cls, session: Session, opportunity: Opportunity, fields: ser.OpportunityCard.Create) -> Self:
        card = OpportunityCard(opportunity=opportunity, title=fields.title, subtitle=fields.subtitle)
        session.add(card)
        return card

    def get_dict(self) -> dict[str, Any]:
        return {
            'opportunity_id': self.opportunity_id,
            'provider_logo_url': self.opportunity.provider.logo_url,
            'provider_name': self.opportunity.provider.name,
            'card_title': self.title,
            'card_subtitle': self.subtitle,
            'tags': self.opportunity.get_tags(),
            'geotags': self.opportunity.get_geotags(),
        }


class OpportunityResponse(Base):
    __tablename__ = 'opportunity_response'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    opportunity_id: Mapped[int] = mapped_column(ForeignKey('opportunity.id'))

    user: Mapped['_user.User'] = relationship(back_populates='responses')
    opportunity: Mapped['Opportunity'] = relationship(back_populates='responses')
    # statuses: Mapped[list['ResponseStatus']] = relationship(back_populates='response')

    @classmethod
    def create(cls, session: Session, user: _user.User, opportunity: 'Opportunity',
               form: '_form.OpportunityForm', data: ser.OpportunityResponse.Data) -> Self | list['_form.FieldError']:
        response = OpportunityResponse(user=user, opportunity=opportunity)
        session.add(response)
        session.flush([response])
        saved_data = _form.ResponseData.create(response=response, form=form, data=data)
        if not isinstance(saved_data, _form.ResponseData):
            return saved_data
        return response
