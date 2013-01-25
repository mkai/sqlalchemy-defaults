from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Column, Boolean, Integer, Unicode, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import false, true

from sqlalchemy_defaults import LazyConfigured, lazy_config_listener


class TestCase(object):
    def setup_method(self, method):
        self.engine = create_engine(
            'postgres://localhost/sqlalchemy_defaults_test'
        )
        self.Model = declarative_base()

        self.User = self.create_user_model(**self.column_options)
        sa.orm.configure_mappers()
        self.columns = self.User.__table__.c
        self.Model.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def teardown_method(self, method):
        self.session.close_all()
        self.Model.metadata.drop_all(self.engine)
        self.engine.dispose()

    def create_user_model(self, **options):
        class User(self.Model, LazyConfigured):
            __tablename__ = 'user'

            id = Column(Integer, primary_key=True)
            name = Column(Unicode(255))
            age = Column(Integer, info={'min': 13, 'max': 120}, default=16)
            is_active = Column(Boolean)
            is_admin = Column(Boolean, default=True)
            hobbies = Column(Unicode(255), default=u'football')
            created_at = Column(sa.DateTime, info={'auto_now': True})

            __lazy_options__ = options

        return User


sa.event.listen(
    sa.orm.mapper,
    'mapper_configured',
    lazy_config_listener
)


class TestLazyConfigurableDefaults(TestCase):
    column_options = {}

    def test_creates_min_and_max_check_constraints(self):
        from sqlalchemy.schema import CreateTable

        sql = str(CreateTable(self.User.__table__).compile(self.engine))
        assert 'CHECK (age >= 13)' in sql
        assert 'CHECK (age <= 120)' in sql

    def test_booleans_not_nullable(self):
        assert self.columns.is_active.nullable is False

    def test_booleans_false(self):
        assert self.columns.is_active.default.arg is False

    def test_assigns_boolean_server_defaults(self):
        is_admin = self.columns.is_admin
        is_active = self.columns.is_active
        assert is_admin.default.arg is True

        assert is_admin.server_default.arg.__class__ == true().__class__
        assert is_active.server_default.arg.__class__ == false().__class__

    def test_strings_not_nullable(self):
        assert self.columns.name.nullable is False

    def test_assigns_string_server_defaults(self):
        assert self.columns.hobbies.server_default.arg == u'football'

    def test_assigns_int_server_defaults(self):
        assert self.columns.age.server_default.arg == '16'

    def test_assigns_auto_now_defaults(self):
        created_at = self.columns.created_at
        assert created_at.default
        assert (
            created_at.server_default.arg.__class__ ==
            sa.func.now().__class__
        )


class TestLazyConfigurableOptionOverriding(TestCase):
    column_options = {
        'min_max_check_constraints': False,
        'string_defaults': False,
        'integer_defaults': False,
        'boolean_defaults': False,
        'auto_now': False
    }

    def test_check_constraints(self):
        from sqlalchemy.schema import CreateTable

        sql = str(CreateTable(self.User.__table__).compile(self.engine))
        assert 'CHECK (age >= 13)' not in sql
        assert 'CHECK (age <= 120)' not in sql

    def test_booleans_defaults(self):
        assert self.columns.is_active.nullable is True
        assert self.columns.is_active.default is None

        is_admin = self.columns.is_admin
        is_active = self.columns.is_active
        assert is_admin.server_default is None
        assert is_active.server_default is None

    def test_string_defaults(self):
        assert self.columns.name.nullable is True
        assert self.columns.hobbies.server_default is None

    def test_integer_defaults(self):
        assert self.columns.age.server_default is None

    def test_auto_now(self):
        created_at = self.columns.created_at
        assert not created_at.default
        assert not created_at.server_default
