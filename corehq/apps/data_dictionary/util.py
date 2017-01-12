from corehq import toggles
from corehq.apps.app_manager.dbaccessors import get_case_types_from_apps
from corehq.apps.app_manager.util import all_case_properties_by_domain, ParentCasePropertyBuilder
from corehq.apps.data_dictionary.models import CaseProperty, CaseType, CaseRelationship
from corehq.apps.export.models.new import CaseExportDataSchema


class OldExportsEnabledException(Exception):
    pass


def generate_data_dictionary(domain):
    if toggles.OLD_EXPORTS.enabled(domain):
        raise OldExportsEnabledException()
    properties = _get_all_case_properties(domain)
    _create_properties_for_case_types(domain, properties)
    CaseType.objects.filter(domain=domain, name__in=properties.keys()).update(fully_generated=True)
    return True


def _get_all_case_properties(domain):
    case_type_to_properties = {}
    case_properties_from_apps = all_case_properties_by_domain(
        domain, include_parent_properties=False
    )

    for case_type in get_case_types_from_apps(domain):
        properties = set()
        schema = CaseExportDataSchema.generate_schema_from_builds(domain, None, case_type)
        for group_schema in schema.group_schemas:
            for item in group_schema.items:
                if item.tag:
                    name = item.tag
                else:
                    name = '/'.join([p.name for p in item.path])
                properties.add(name)

        case_type_props_from_app = case_properties_from_apps.get(case_type, {})
        properties |= set(case_type_props_from_app)

        case_type_to_properties[case_type] = properties

    return case_type_to_properties


def _get_current_case_types_and_properties(domain):
    properties = {}
    case_types = {}

    db_case_types = CaseType.objects.filter(domain=domain).prefetch_related('properties')
    for case_type in db_case_types:
        case_types[case_type.name] = case_type
        properties[case_type.name] = set()
        for prop in case_type.properties.all():
            case_type = prop.case_type.name
            properties[case_type].add(prop.name)

    return case_types, properties


def add_properties_to_data_dictionary(domain, case_type, properties):
    if properties:
        _create_properties_for_case_types(domain, {case_type: properties})


def _create_properties_for_case_types(domain, case_type_to_prop):
    current_case_types, current_properties = _get_current_case_types_and_properties(domain)
    new_case_properties = []

    for case_type, props in case_type_to_prop.items():
        if not case_type:
            continue

        try:
            case_type_obj = current_case_types[case_type]
        except KeyError:
            case_type_obj = CaseType.objects.create(domain=domain, name=case_type)

        for prop in props:
            # don't add any properites to parent cases
            if '/' in prop:
                continue

            if (case_type not in current_properties or
                    prop not in current_properties[case_type]):
                new_case_properties.append(CaseProperty(
                    case_type=case_type_obj, name=prop
                ))

    CaseProperty.objects.bulk_create(new_case_properties)


def generate_case_hierarchy(app, case_types):
    builder = ParentCasePropertyBuilder(app)
    parent_type_map = builder.get_parent_type_map(case_types, allow_multiple_parents=True)
    for case_type, relationships in parent_type_map:
        case_type = CaseType.objects.get(domain=app.domain, name=case_type)
        for relationship, parent_types in relationships:
            for parent in parent_types:
                referenced_case_type = CaseType.objects.get_or_create(domain=app.domain, name=parent)

                CaseRelationship(
                    case_type=case_type,
                    referenced_case_type=referenced_case_type
                    reference_id=relationship
                ).save()
