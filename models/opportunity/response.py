from typing import Self

from ...utils import *
from ..base import *
from .. import user as _user
from ..opportunity import opportunity as _opportunity
from ...serializers import mod as ser


# class CreateResponseStatusErrorCode(IntEnum):
#     INVALID_RESPONSE_ID = 0

# class ResponseStatus(Base):
#     __tablename__ = 'response_status'

#     id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
#     response_id: Mapped[int] = mapped_column(ForeignKey('opportunity_response.id'))
#     status: Mapped[str] = mapped_column(String(50))
#     description: Mapped[str | None] = mapped_column(String(200), nullable=True)
#     timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

#     response: Mapped['OpportunityResponse'] = relationship(back_populates='statuses')

#     @classmethod
#     def create_initial(cls, session: Session, response: 'OpportunityResponse') -> Self:
#         status = ResponseStatus(
#             response=response,
#             status='Response created',
#             description=None,
#             timestamp=datetime.now(),
#         )
#         session.add(status)
#         return status

#     @classmethod
#     def create(cls, session: Session, request: ser.ResponseStatus.Create) \
#             -> Self | GenericError[CreateResponseStatusErrorCode]:
#         response: OpportunityResponse | None = session.query(OpportunityResponse).get(request.response_id)
#         if response is None:
#             logger.debug('\'ResponseStatus.create\' exited with \'INVALID_RESPONSE_ID\' error (id=%i)',
#                          request.response_id)
#             return GenericError(
#                 error_code=CreateResponseStatusErrorCode.INVALID_RESPONSE_ID,
#                 error_message='Opportunity response with given id doesn\'t exist',
#             )
#         status = ResponseStatus(
#             response=response,
#             status=request.status,
#             description=request.description,
#             timestamp=request.timestamp,
#         )
#         session.add(status)
#         return status


class OpportunityResponse(Base):
    __tablename__ = 'opportunity_response'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    opportunity_id: Mapped[int] = mapped_column(ForeignKey('opportunity.id'))

    user: Mapped['_user.User'] = relationship(back_populates='responses')
    opportunity: Mapped['_opportunity.Opportunity'] = relationship(back_populates='responses')
    # statuses: Mapped[list['ResponseStatus']] = relationship(back_populates='response')

    @classmethod
    def create(cls, session: Session, user: _user.User, opportunity: _opportunity.Opportunity,
               form: '_form.OpportunityForm', data: ser.OpportunityResponse.Create) -> Self | list[_form.FieldError]:
        response = OpportunityResponse(user=user, opportunity=opportunity)
        session.add(response)
        session.flush([response])
        saved_data = _form.ResponseData.create(response_id=response.id, form=form, data=data)
        if not isinstance(saved_data, _form.ResponseData):
            return saved_data
        return response


from ..opportunity import form as _form
