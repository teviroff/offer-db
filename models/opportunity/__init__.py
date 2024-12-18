from .opportunity import (
    Opportunity, OpportunityProvider,
    CreateOpportunityTagErrorCode, OpportunityTag,
    CreateOpportunityGeotagErrorCode, OpportunityGeotag,
    OpportunityToTag, OpportunityToGeotag,
    OpportunityCard, OpportunityResponse,
)
from .form import (
    SubmitMethod, NoopSubmitMethod, YandexFormsSubmitMethod,
    FormField, StringField, RegexField, ChoiceField,
    OpportunityForm, ResponseData,
)
