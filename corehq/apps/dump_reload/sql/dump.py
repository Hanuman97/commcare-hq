from collections import OrderedDict

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.db import router
from django.db.models import Q

from corehq.apps.dump_reload.exceptions import DomainDumpError
from corehq.apps.dump_reload.sql.serialization import JsonLinesSerializer
from corehq.sql_db.config import partition_config

APP_LABELS_WITH_FILTER_KWARGS_TO_DUMP = {
    'locations.LocationType': 'domain',
    'locations.SQLLocation': 'domain',
    'form_processor.XFormInstanceSQL': 'domain',
    'form_processor.XFormAttachmentSQL': 'form__domain',
    'form_processor.XFormOperationSQL': 'form__domain',
    'form_processor.CommCareCaseSQL': 'domain',
    'form_processor.CommCareCaseIndexSQL': 'domain',
    'form_processor.CaseTransaction': 'case__domain',
}


def dump_sql_data(domain, excludes, output_stream):
    """
    Dump SQL data for domain to stream.
    :param domain: Name of domain to dump data for
    :param excludes: List of app labels ("app_label.model_name" or "app_label") to exclude
    :param output_stream: Stream to write json encoded objects to
    """
    excluded_apps, excluded_models = get_excluded_apps_and_models(excludes)
    app_config_models = _get_app_list(excluded_apps)
    objects = get_objects_to_dump(domain, app_config_models, excluded_models)
    JsonLinesSerializer().serialize(
        objects,
        use_natural_foreign_keys=False,
        use_natural_primary_keys=False,
        stream=output_stream
    )


def get_objects_to_dump(domain, app_config_models, excluded_models):
    """
    :param domain: domain name to filter with
    :param app_list: List of (app_config, model) tuples to dump
    :param excluded_models: List of model classes to exclude
    :return: generator yielding models objects
    """
    # Collate the objects to be serialized.
    for model in serializers.sort_dependencies(app_config_models.items()):
        if model in excluded_models:
            continue

        using = router.db_for_read(model)
        if settings.USE_PARTITIONED_DATABASE and using == partition_config.get_proxy_db():
            using = partition_config.get_form_processing_dbs()
        else:
            using = [using]

        for db_alias in using:
            if not model._meta.proxy and router.allow_migrate_model(db_alias, model):
                objects = model._default_manager

                filter = get_model_domain_filter(model, domain)

                queryset = objects.using(db_alias) \
                    .filter(filter) \
                    .order_by(model._meta.pk.name)

                for obj in queryset.iterator():
                    yield obj


def get_model_domain_filter(model, domain):
    label = '{}.{}'.format(model._meta.app_label, model.__name__)
    filter_kwarg = APP_LABELS_WITH_FILTER_KWARGS_TO_DUMP[label]
    return Q(**{filter_kwarg: domain})


def get_excluded_apps_and_models(excludes):
    """
    :param excludes: list of app labels ("app_label.model_name" or "app_label") to exclude
    :return: Tuple containing two sets: Set of AppConfigs to exclude, Set of model classes to excluded.
    """
    excluded_apps = set()
    excluded_models = set()
    for exclude in excludes:
        if '.' in exclude:
            try:
                model = apps.get_model(exclude)
            except LookupError:
                raise DomainDumpError('Unknown model in excludes: %s' % exclude)
            excluded_models.add(model)
        else:
            try:
                app_config = apps.get_app_config(exclude)
            except LookupError:
                raise DomainDumpError('Unknown app in excludes: %s' % exclude)
            excluded_apps.add(app_config)
    return excluded_apps, excluded_models


def _get_app_list(excluded_apps):
    """
    :return: OrderedDict(app_config, model), ...)
    """
    app_list = OrderedDict()
    for label in APP_LABELS_WITH_FILTER_KWARGS_TO_DUMP:
        app_label, model_label = label.split('.')
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            raise DomainDumpError("Unknown application: %s" % app_label)
        if app_config in excluded_apps:
            continue
        try:
            model = app_config.get_model(model_label)
        except LookupError:
            raise DomainDumpError("Unknown model: %s.%s" % (app_label, model_label))

        app_list_value = app_list.setdefault(app_config, [])

        if model not in app_list_value:
            app_list_value.append(model)

    return app_list
