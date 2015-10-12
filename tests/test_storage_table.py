﻿# coding: utf-8

#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import base64
import unittest
import sys
import locale
import os

from datetime import datetime, timedelta
from dateutil.tz import tzutc, tzoffset
from requests import Session
from math import(
    isnan,
)
from azure.common import (
    AzureHttpError,
    AzureConflictHttpError,
    AzureMissingResourceHttpError,
    AzureException,
)
from azure.storage import (
    AccessPolicy,
    SharedAccessPolicy,
    SignedIdentifier,
    SignedIdentifiers,
)
from azure.storage.table import (
    Entity,
    EntityProperty,
    TableService,
    TableSharedAccessPermissions,
    EdmType,
    TableBatch,
)
from tests.common_recordingtestcase import (
    TestMode,
    record,
)
from tests.storage_testcase import StorageTestCase

#------------------------------------------------------------------------------

MAX_RETRY = 60
#------------------------------------------------------------------------------


class StorageTableTest(StorageTestCase):

    def setUp(self):
        super(StorageTableTest, self).setUp()

        self.ts = self._create_storage_service(TableService, self.settings)

        self.table_name = self.get_resource_name('uttable')

        self.additional_table_names = []

    def tearDown(self):
        if not self.is_playback():
            try:
                self.ts.delete_table(self.table_name)
            except:
                pass

            for name in self.additional_table_names:
                try:
                    self.ts.delete_table(name)
                except:
                    pass

        return super(StorageTableTest, self).tearDown()

    #--Helpers-----------------------------------------------------------------
    def _create_table(self, table_name):
        '''
        Creates a table with the specified name.
        '''
        self.ts.create_table(table_name, True)

    def _create_table_with_default_entities(self, table_name, entity_count):
        '''
        Creates a table with the specified name and adds entities with the
        default set of values. PartitionKey is set to 'MyPartition' and RowKey
        is set to a unique counter value starting at 1 (as a string).
        '''
        entities = []
        self._create_table(table_name)
        for i in range(1, entity_count + 1):
            entities.append(self.ts.insert_entity(
                table_name,
                self._create_default_entity_dict('MyPartition', str(i))))
        return entities

    def _create_default_entity_class(self, partition, row):
        '''
        Creates a class-based entity with fixed values, using all
        of the supported data types.
        '''
        entity = Entity()
        entity.PartitionKey = partition
        entity.RowKey = row
        entity.age = 39
        entity.sex = 'male'
        entity.married = True
        entity.deceased = False
        entity.optional = None
        entity.evenratio = 3.0
        entity.ratio = 3.1
        entity.large = 933311100
        entity.Birthday = datetime(1973, 10, 4)
        entity.birthday = datetime(1970, 10, 4)
        entity.binary = None
        entity.other = EntityProperty(EdmType.INT32, 20)
        entity.clsid = EntityProperty(
            EdmType.GUID, 'c9da6455-213d-42c9-9a79-3e9149a57833')
        return entity

    def _create_default_entity_dict(self, partition, row):
        '''
        Creates a dictionary-based entity with fixed values, using all
        of the supported data types.
        '''
        return {'PartitionKey': partition,
                'RowKey': row,
                'age': 39,
                'sex': 'male',
                'married': True,
                'deceased': False,
                'optional': None,
                'ratio': 3.1,
                'evenratio': 3.0,
                'large': 933311100,
                'Birthday': datetime(1973, 10, 4),
                'birthday': datetime(1970, 10, 4),
                'other': EntityProperty(EdmType.INT32, 20),
                'clsid': EntityProperty(
                    EdmType.GUID,
                    'c9da6455-213d-42c9-9a79-3e9149a57833')}

    def _create_updated_entity_dict(self, partition, row):
        '''
        Creates a dictionary-based entity with fixed values, with a
        different set of values than the default entity. It
        adds fields, changes field values, changes field types,
        and removes fields when compared to the default entity.
        '''
        return {'PartitionKey': partition,
                'RowKey': row,
                'age': 'abc',
                'sex': 'female',
                'sign': 'aquarius',
                'birthday': datetime(1991, 10, 4)}

    def _assert_default_entity(self, entity):
        '''
        Asserts that the entity passed in matches the default entity.
        '''
        self.assertEqual(entity.age, 39)
        self.assertEqual(entity.sex, 'male')
        self.assertEqual(entity.married, True)
        self.assertEqual(entity.deceased, False)
        self.assertFalse(hasattr(entity, "optional"))
        self.assertFalse(hasattr(entity, "aquarius"))
        self.assertEqual(entity.ratio, 3.1)
        self.assertEqual(entity.evenratio, 3.0)
        self.assertEqual(entity.large, 933311100)
        self.assertEqual(entity.Birthday, datetime(1973, 10, 4, tzinfo=tzutc()))
        self.assertEqual(entity.birthday, datetime(1970, 10, 4, tzinfo=tzutc()))
        self.assertIsInstance(entity.other, EntityProperty)
        self.assertEqual(entity.other.type, EdmType.INT32)
        self.assertEqual(entity.other.value, 20)
        self.assertIsInstance(entity.clsid, EntityProperty)
        self.assertEqual(entity.clsid.type, EdmType.GUID)
        self.assertEqual(entity.clsid.value,
                         'c9da6455-213d-42c9-9a79-3e9149a57833')
        self.assertTrue(hasattr(entity, "Timestamp"))
        self.assertIsInstance(entity.Timestamp, datetime)
        self.assertIsNotNone(entity.etag)

    def _assert_default_entity_json_no_metadata(self, entity):
        '''
        Asserts that the entity passed in matches the default entity.
        '''
        self.assertEqual(entity.age, '39')
        self.assertEqual(entity.sex, 'male')
        self.assertEqual(entity.married, True)
        self.assertEqual(entity.deceased, False)
        self.assertFalse(hasattr(entity, "optional"))
        self.assertFalse(hasattr(entity, "aquarius"))
        self.assertEqual(entity.ratio, 3.1)
        self.assertEqual(entity.evenratio, 3.0)
        self.assertEqual(entity.large, '933311100')
        self.assertEqual(entity.Birthday, '1973-10-04T00:00:00Z')
        self.assertEqual(entity.birthday, '1970-10-04T00:00:00Z')
        self.assertIsInstance(entity.other, EntityProperty)
        self.assertEqual(entity.other.type, EdmType.INT32)
        self.assertEqual(entity.other.value, 20)
        self.assertEqual(entity.clsid, 'c9da6455-213d-42c9-9a79-3e9149a57833')
        self.assertTrue(hasattr(entity, "Timestamp"))
        self.assertIsInstance(entity.Timestamp, datetime)
        self.assertIsNotNone(entity.etag)

    def _assert_updated_entity(self, entity):
        '''
        Asserts that the entity passed in matches the updated entity.
        '''
        self.assertEqual(entity.age, 'abc')
        self.assertEqual(entity.sex, 'female')
        self.assertFalse(hasattr(entity, "married"))
        self.assertFalse(hasattr(entity, "deceased"))
        self.assertEqual(entity.sign, 'aquarius')
        self.assertFalse(hasattr(entity, "optional"))
        self.assertFalse(hasattr(entity, "ratio"))
        self.assertFalse(hasattr(entity, "evenratio"))
        self.assertFalse(hasattr(entity, "large"))
        self.assertFalse(hasattr(entity, "Birthday"))
        self.assertEqual(entity.birthday, datetime(1991, 10, 4, tzinfo=tzutc()))
        self.assertFalse(hasattr(entity, "other"))
        self.assertFalse(hasattr(entity, "clsid"))
        self.assertTrue(hasattr(entity, "Timestamp"))
        self.assertIsNotNone(entity.etag)

    def _assert_merged_entity(self, entity):
        '''
        Asserts that the entity passed in matches the default entity
        merged with the updated entity.
        '''
        self.assertEqual(entity.age, 'abc')
        self.assertEqual(entity.sex, 'female')
        self.assertEqual(entity.sign, 'aquarius')
        self.assertEqual(entity.married, True)
        self.assertEqual(entity.deceased, False)
        self.assertEqual(entity.sign, 'aquarius')
        self.assertEqual(entity.ratio, 3.1)
        self.assertEqual(entity.evenratio, 3.0)
        self.assertEqual(entity.large, 933311100)
        self.assertEqual(entity.Birthday, datetime(1973, 10, 4, tzinfo=tzutc()))
        self.assertEqual(entity.birthday, datetime(1991, 10, 4, tzinfo=tzutc()))
        self.assertIsInstance(entity.other, EntityProperty)
        self.assertEqual(entity.other.type, EdmType.INT32)
        self.assertEqual(entity.other.value, 20)
        self.assertIsInstance(entity.clsid, EntityProperty)
        self.assertEqual(entity.clsid.type, EdmType.GUID)
        self.assertEqual(entity.clsid.value,
                         'c9da6455-213d-42c9-9a79-3e9149a57833')
        self.assertTrue(hasattr(entity, "Timestamp"))
        self.assertIsNotNone(entity.etag)

    def _resolver_with_assert(self, pk, rk, name, value, type):
        self.assertIsNotNone(pk)
        self.assertIsNotNone(rk)
        self.assertIsNotNone(name)
        self.assertIsNotNone(value)
        self.assertIsNone(type)
        if name == 'large' or name == 'age':
            return EdmType.INT64
        if name == 'Birthday' or name == 'birthday':
            return EdmType.DATETIME
        if name == 'clsid':
            return EdmType.GUID

    def _get_shared_access_policy(self, permission):
        date_format = "%Y-%m-%dT%H:%M:%SZ"
        start = datetime.utcnow() - timedelta(minutes=1)
        expiry = start + timedelta(hours=1)
        return SharedAccessPolicy(
            AccessPolicy(
                start.strftime(date_format),
                expiry.strftime(date_format),
                permission
            )
        )

    #--Test cases for tables --------------------------------------------------
    @record
    def test_create_table(self):
        # Arrange

        # Act
        created = self.ts.create_table(self.table_name)

        # Assert
        self.assertTrue(created)

    @record
    def test_create_table_fail_on_exist(self):
        # Arrange

        # Act
        created = self.ts.create_table(self.table_name, True)

        # Assert
        self.assertTrue(created)

    @record
    def test_create_table_with_already_existing_table(self):
        # Arrange

        # Act
        created1 = self.ts.create_table(self.table_name)
        created2 = self.ts.create_table(self.table_name)

        # Assert
        self.assertTrue(created1)
        self.assertFalse(created2)

    @record
    def test_create_table_with_already_existing_table_fail_on_exist(self):
        # Arrange

        # Act
        created = self.ts.create_table(self.table_name)
        with self.assertRaises(AzureConflictHttpError):
            self.ts.create_table(self.table_name, True)

        # Assert
        self.assertTrue(created)

    @record
    def test_query_tables(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        tables = []
        next=None
        while True:
            segment = self.ts.query_tables(next_table_name=next)
            for table in segment:
                tables.append(table)

            next = None
            if hasattr(segment, 'x_ms_continuation'):
                next = segment.x_ms_continuation.get('nexttablename')
            if not next:
                break

        # Assert
        tableNames = [x.name for x in tables]
        self.assertGreaterEqual(len(tableNames), 1)
        self.assertGreaterEqual(len(tables), 1)
        self.assertIn(self.table_name, tableNames)

    @record
    def test_query_tables_with_table_name(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        tables = self.ts.query_tables(self.table_name)
        for table in tables:
            pass

        # Assert
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].name, self.table_name)

    @record
    def test_query_tables_with_table_name_no_tables(self):
        # Arrange

        # Act
        with self.assertRaises(AzureHttpError):
            self.ts.query_tables(self.table_name)

        # Assert

    @record
    def test_query_tables_with_top(self):
        # Arrange
        self.additional_table_names = [
            self.table_name + suffix for suffix in 'abcd']
        for name in self.additional_table_names:
            self.ts.create_table(name)

        # Act
        tables = self.ts.query_tables(None, 3)
        for table in tables:
            pass

        # Assert
        self.assertEqual(len(tables), 3)

    @record
    def test_query_tables_with_top_and_next_table_name(self):
        # Arrange
        self.additional_table_names = [
            self.table_name + suffix for suffix in 'abcd']
        for name in self.additional_table_names:
            self.ts.create_table(name)

        # Act
        tables_set1 = self.ts.query_tables(None, 3)
        tables_set2 = self.ts.query_tables(
            None, 3, tables_set1.x_ms_continuation['NextTableName'])

        # Assert
        self.assertEqual(len(tables_set1), 3)
        self.assertGreaterEqual(len(tables_set2), 1)
        self.assertLessEqual(len(tables_set2), 3)

    @record
    def test_delete_table_with_existing_table(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        deleted = self.ts.delete_table(self.table_name)

        # Assert
        self.assertTrue(deleted)
        tables = self.ts.query_tables()
        self.assertNamedItemNotInContainer(tables, self.table_name)

    @record
    def test_delete_table_with_existing_table_fail_not_exist(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        deleted = self.ts.delete_table(self.table_name, True)

        # Assert
        self.assertTrue(deleted)
        tables = self.ts.query_tables()
        self.assertNamedItemNotInContainer(tables, self.table_name)

    @record
    def test_delete_table_with_non_existing_table(self):
        # Arrange

        # Act
        deleted = self.ts.delete_table(self.table_name)

        # Assert
        self.assertFalse(deleted)

    @record
    def test_delete_table_with_non_existing_table_fail_not_exist(self):
        # Arrange

        # Act
        with self.assertRaises(AzureMissingResourceHttpError):
            self.ts.delete_table(self.table_name, True)

        # Assert

    #--Test cases for entities ------------------------------------------
    @record
    def test_insert_entity_dictionary(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        dict = self._create_default_entity_dict('MyPartition', '1')
        resp = self.ts.insert_entity(self.table_name, dict)

        # Assert
        self.assertIsNotNone(resp)

    @record
    def test_insert_entity_class_instance(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        entity = self._create_default_entity_class('MyPartition', '1')
        resp = self.ts.insert_entity(self.table_name, entity)

        # Assert
        self.assertIsNotNone(resp)

    @record
    def test_insert_entity_conflict(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        with self.assertRaises(AzureConflictHttpError):
            self.ts.insert_entity(
                self.table_name,
                self._create_default_entity_dict('MyPartition', '1'))

        # Assert

    @record
    def test_insert_entity_with_large_int32_value_throws(self):
        # Arrange

        # Act
        dict32 = {'PartitionKey': 'MyPartition',
                'RowKey': '1',
                'large': EntityProperty(EdmType.INT32, 2**15)}

        # Assert
        with self.assertRaisesRegexp(TypeError, 
                               '{0} is too large to be cast to type Edm.Int32.'.format(2**15)):
            self.ts.insert_entity(self.table_name, dict32)

    @record
    def test_insert_entity_with_large_int64_value_throws(self):
        # Arrange

        # Act
        dict64 = {'PartitionKey': 'MyPartition',
                'RowKey': '1',
                'large': 2**31}

        # Assert
        with self.assertRaisesRegexp(TypeError, 
                               '{0} is too large to be cast to type Edm.Int64.'.format(2**31)):
            self.ts.insert_entity(self.table_name, dict64)

    def test_insert_entity_missing_pk(self):
        # Arrange
        entity = {'RowKey': 'rk'}

        # Act
        with self.assertRaises(ValueError):
            resp = self.ts.insert_entity(self.table_name, entity)

        # Assert

    @record
    def test_insert_entity_missing_rk(self):
        # Arrange
        entity = {'PartitionKey': 'pk'}

        # Act
        with self.assertRaises(ValueError):
            resp = self.ts.insert_entity(self.table_name, entity)

        # Assert

    @record
    def test_insert_entity_too_many_properties(self):
        # Arrange
        entity = {}
        for i in range(255):
            entity['key{0}'.format(i)] = 'value{0}'.format(i)

        # Act
        with self.assertRaises(ValueError):
            resp = self.ts.insert_entity(self.table_name, entity)

        # Assert

    @record
    def test_insert_entity_property_name_too_long(self):
        # Arrange
        str = 'a'*256
        entity = {
            'PartitionKey': 'pk',
            'RowKey': 'rk',
            str: 'badval'
            }

        # Act
        with self.assertRaises(ValueError):
            resp = self.ts.insert_entity(self.table_name, entity)

        # Assert

    @record
    def test_get_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.get_entity(self.table_name, 'MyPartition', '1')

        # Assert
        self.assertEqual(resp.PartitionKey, 'MyPartition')
        self.assertEqual(resp.RowKey, '1')
        self._assert_default_entity(resp)

    @record
    def test_get_entity_if_match(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        # Do a get and confirm the etag is parsed correctly by using it
        # as a condition to delete.
        resp = self.ts.get_entity(self.table_name, 'MyPartition', '1')
        resp = self.ts.delete_entity(self.table_name, resp.PartitionKey, 
                                     resp.RowKey, if_match=resp.etag)

        # Assert

    @record
    def test_get_entity_full_metadata(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.get_entity(self.table_name, 'MyPartition', '1',
                                  accept='application/json;odata=fullmetadata')

        # Assert
        self.assertEqual(resp.PartitionKey, 'MyPartition')
        self.assertEqual(resp.RowKey, '1')
        self._assert_default_entity(resp)

    @record
    def test_get_entity_no_metadata(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.get_entity(self.table_name, 'MyPartition', '1',
                                  accept='application/json;odata=nometadata')

        # Assert
        self.assertEqual(resp.PartitionKey, 'MyPartition')
        self.assertEqual(resp.RowKey, '1')
        self._assert_default_entity_json_no_metadata(resp)

    @record
    def test_get_entity_with_property_resolver(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.get_entity(self.table_name, 'MyPartition', '1',
                                  accept='application/json;odata=nometadata',
                                  property_resolver=self._resolver_with_assert)

        # Assert
        self.assertEqual(resp.PartitionKey, 'MyPartition')
        self.assertEqual(resp.RowKey, '1')
        self._assert_default_entity(resp)

    @record
    def test_get_entity_with_property_resolver_not_supported(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        with self.assertRaisesRegexp(AzureException, 
                               'Type not supported when sending data to the service:'):
            self.ts.get_entity(self.table_name, 'MyPartition', '1',
                               property_resolver=lambda pk, rk, name, val, type: 'badType')

        # Assert

    @record
    def test_get_entity_with_property_resolver_invalid(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        with self.assertRaisesRegexp(AzureException, 
                               'The specified property resolver returned an invalid type.'):
            self.ts.get_entity(self.table_name, 'MyPartition', '1',
                               property_resolver=lambda pk, rk, name, val, type: EdmType.INT64)

        # Assert

    @record
    def test_get_entity_not_existing(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        with self.assertRaises(AzureMissingResourceHttpError):
            self.ts.get_entity(self.table_name, 'MyPartition', '1')

        # Assert

    @record
    def test_get_entity_with_select(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.get_entity(
            self.table_name, 'MyPartition', '1', 'age,sex,xyz')

        # Assert
        self.assertEqual(resp.age, 39)
        self.assertEqual(resp.sex, 'male')
        self.assertEqual(resp.xyz, None)
        self.assertFalse(hasattr(resp, "birthday"))
        self.assertFalse(hasattr(resp, "married"))
        self.assertFalse(hasattr(resp, "deceased"))

    @record
    def test_get_entity_with_special_doubles(self):
        # Arrange
        self._create_table(self.table_name)

        entity = {'PartitionKey': 'MyPartition',
                'RowKey': 'MyRowKey',
                'inf': float('inf'),
                'negativeinf': float('-inf'),
                'nan': float('nan')}
        self.ts.insert_entity(self.table_name, entity)

        # Act
        resp = self.ts.get_entity(
            self.table_name, 'MyPartition', 'MyRowKey')

        # Assert
        self.assertEqual(resp.inf, float('inf'))
        self.assertEqual(resp.negativeinf, float('-inf'))
        self.assertTrue(isnan(resp.nan))

    @record
    def test_query_entities(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)

        # Act
        resp = self.ts.query_entities(self.table_name)

        # Assert
        self.assertEqual(len(resp), 2)
        for entity in resp:
            self.assertEqual(entity.PartitionKey, 'MyPartition')
            self._assert_default_entity(entity)
        self.assertEqual(resp[0].RowKey, '1')
        self.assertEqual(resp[1].RowKey, '2')

    @record
    def test_query_entities_full_metadata(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)

        # Act
        resp = self.ts.query_entities(self.table_name, 
                                      accept='application/json;odata=fullmetadata')

        # Assert
        self.assertEqual(len(resp), 2)
        for entity in resp:
            self.assertEqual(entity.PartitionKey, 'MyPartition')
            self._assert_default_entity(entity)
            self.assertIsNotNone(entity.etag)
        self.assertEqual(resp[0].RowKey, '1')
        self.assertEqual(resp[1].RowKey, '2')

    @record
    def test_query_entities_no_metadata(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)

        # Act
        resp = self.ts.query_entities(self.table_name, 
                                      accept='application/json;odata=nometadata')

        # Assert
        self.assertEqual(len(resp), 2)
        for entity in resp:
            self.assertEqual(entity.PartitionKey, 'MyPartition')
            self._assert_default_entity_json_no_metadata(entity)
        self.assertEqual(resp[0].RowKey, '1')
        self.assertEqual(resp[1].RowKey, '2')

    @record
    def test_query_entities_with_property_resolver(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)

        # Act
        resp = self.ts.query_entities(self.table_name, 
                                      accept='application/json;odata=nometadata',
                                      property_resolver=self._resolver_with_assert)

        # Assert
        self.assertEqual(len(resp), 2)
        for entity in resp:
            self.assertEqual(entity.PartitionKey, 'MyPartition')
            self._assert_default_entity(entity)
        self.assertEqual(resp[0].RowKey, '1')
        self.assertEqual(resp[1].RowKey, '2')

    @record
    def test_query_entities_large(self):
        # Arrange
        self._create_table(self.table_name)
        total_entities_count = 1000
        entities_per_batch = 50

        for j in range(total_entities_count // entities_per_batch):
            batch = TableBatch()
            for i in range(entities_per_batch):
                entity = Entity()
                entity.PartitionKey = 'large'
                entity.RowKey = 'batch{0}-item{1}'.format(j, i)
                entity.test = EntityProperty(EdmType.BOOLEAN, 'true')
                entity.test2 = 'hello world;' * 100
                entity.test3 = 3
                entity.test4 = EntityProperty(EdmType.INT64, '1234567890')
                entity.test5 = datetime(2016, 12, 31, 11, 59, 59, 0)
                batch.insert_entity(entity)
            self.ts.commit_batch(self.table_name, batch)

        # Act
        start_time = datetime.now()
        resp = self.ts.query_entities(self.table_name)
        elapsed_time = datetime.now() - start_time

        # Assert
        print('query_entities took {0} secs.'.format(elapsed_time.total_seconds()))
        # azure allocates 5 seconds to execute a query
        # if it runs slowly, it will return fewer results and make the test fail
        self.assertEqual(len(resp), total_entities_count)

    @record
    def test_query_entities_with_filter(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)
        self.ts.insert_entity(
            self.table_name,
            self._create_default_entity_dict('MyOtherPartition', '3'))

        # Act
        resp = self.ts.query_entities(
            self.table_name, "PartitionKey eq 'MyPartition'")

        # Assert
        self.assertEqual(len(resp), 2)
        for entity in resp:
            self.assertEqual(entity.PartitionKey, 'MyPartition')
            self._assert_default_entity(entity)

    @record
    def test_query_entities_with_select(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)

        # Act
        resp = self.ts.query_entities(self.table_name, None, 'age,sex')

        # Assert
        self.assertEqual(len(resp), 2)
        self.assertEqual(resp[0].age, 39)
        self.assertEqual(resp[0].sex, 'male')
        self.assertFalse(hasattr(resp[0], "birthday"))
        self.assertFalse(hasattr(resp[0], "married"))
        self.assertFalse(hasattr(resp[0], "deceased"))

    @record
    def test_query_entities_with_top(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 3)

        # Act
        resp = self.ts.query_entities(self.table_name, None, None, 2)

        # Assert
        self.assertEqual(len(resp), 2)

    @record
    def test_query_entities_with_top_and_next(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 5)

        # Act
        resp1 = self.ts.query_entities(self.table_name, None, None, 2)
        resp2 = self.ts.query_entities(
            self.table_name, None, None, 2,
            resp1.x_ms_continuation['NextPartitionKey'],
            resp1.x_ms_continuation['NextRowKey'])
        resp3 = self.ts.query_entities(
            self.table_name, None, None, 2,
            resp2.x_ms_continuation['NextPartitionKey'],
            resp2.x_ms_continuation['NextRowKey'])

        # Assert
        self.assertEqual(len(resp1), 2)
        self.assertEqual(len(resp2), 2)
        self.assertEqual(len(resp3), 1)
        self.assertEqual(resp1[0].RowKey, '1')
        self.assertEqual(resp1[1].RowKey, '2')
        self.assertEqual(resp2[0].RowKey, '3')
        self.assertEqual(resp2[1].RowKey, '4')
        self.assertEqual(resp3[0].RowKey, '5')

    @record
    def test_update_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.update_entity(self.table_name, sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    @record
    def test_update_entity_with_if_matches(self):
        # Arrange
        etags = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.update_entity(
            self.table_name, sent_entity, if_match=etags[0])

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    @record
    def test_update_entity_with_if_doesnt_match(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        with self.assertRaises(AzureHttpError):
            self.ts.update_entity(
                self.table_name, sent_entity,
                if_match=u'W/"datetime\'2012-06-15T22%3A51%3A44.9662825Z\'"')

        # Assert

    @record
    def test_insert_or_merge_entity_with_existing_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.insert_or_merge_entity(self.table_name, sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_merged_entity(received_entity)

    @record
    def test_insert_or_merge_entity_with_non_existing_entity(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.insert_or_merge_entity(self.table_name, sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(
            self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    @record
    def test_insert_or_replace_entity_with_existing_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.insert_or_replace_entity(self.table_name, sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    @record
    def test_insert_or_replace_entity_with_non_existing_entity(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.insert_or_replace_entity(self.table_name, sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    @record
    def test_merge_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.merge_entity(self.table_name, sent_entity)

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(self.table_name, 'MyPartition', '1')
        self._assert_merged_entity(received_entity)

    @record
    def test_merge_entity_not_existing(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        with self.assertRaises(AzureHttpError):
            self.ts.merge_entity(self.table_name, sent_entity)

        # Assert

    @record
    def test_merge_entity_with_if_matches(self):
        # Arrange
        etags = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = self.ts.merge_entity(self.table_name,
            sent_entity, if_match=etags[0])

        # Assert
        self.assertIsNotNone(resp)
        received_entity = self.ts.get_entity(self.table_name, 'MyPartition', '1')
        self._assert_merged_entity(received_entity)

    @record
    def test_merge_entity_with_if_doesnt_match(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        sent_entity = self._create_updated_entity_dict('MyPartition', '1')
        with self.assertRaises(AzureHttpError):
            self.ts.merge_entity(
                self.table_name, sent_entity,
                if_match=u'W/"datetime\'2012-06-15T22%3A51%3A44.9662825Z\'"')

        # Assert

    @record
    def test_delete_entity(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.delete_entity(self.table_name, 'MyPartition', '1')

        # Assert
        self.assertIsNone(resp)
        with self.assertRaises(AzureHttpError):
            self.ts.get_entity(self.table_name, 'MyPartition', '1')

    @record
    def test_delete_entity_not_existing(self):
        # Arrange
        self._create_table(self.table_name)

        # Act
        with self.assertRaises(AzureHttpError):
            self.ts.delete_entity(self.table_name, 'MyPartition', '1')

        # Assert

    @record
    def test_delete_entity_with_if_matches(self):
        # Arrange
        etags = self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.delete_entity(
            self.table_name, 'MyPartition', '1', if_match=etags[0])

        # Assert
        self.assertIsNone(resp)
        with self.assertRaises(AzureHttpError):
            self.ts.get_entity(self.table_name, 'MyPartition', '1')

    @record
    def test_delete_entity_with_if_doesnt_match(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        with self.assertRaises(AzureHttpError):
            self.ts.delete_entity(
                self.table_name, 'MyPartition', '1',
                if_match=u'W/"datetime\'2012-06-15T22%3A51%3A44.9662825Z\'"')

        # Assert

    @record
    def test_with_filter_single(self):
        called = []

        def my_filter(request, next):
            called.append(True)
            return next(request)

        tc = self.ts.with_filter(my_filter)
        tc.create_table(self.table_name)

        self.assertTrue(called)

        del called[:]

        tc.delete_table(self.table_name)

        self.assertTrue(called)
        del called[:]

    @record
    def test_with_filter_chained(self):
        called = []

        def filter_a(request, next):
            called.append('a')
            return next(request)

        def filter_b(request, next):
            called.append('b')
            return next(request)

        tc = self.ts.with_filter(filter_a).with_filter(filter_b)
        tc.create_table(self.table_name)

        self.assertEqual(called, ['b', 'a'])

        tc.delete_table(self.table_name)

    @record
    def test_unicode_property_value(self):
        ''' regression test for github issue #57'''
        # Act
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {'PartitionKey': 'test', 'RowKey': 'test1', 'Description': u'ꀕ'})
        self.ts.insert_entity(
            self.table_name,
            {'PartitionKey': 'test', 'RowKey': 'test2', 'Description': 'ꀕ'})
        resp = self.ts.query_entities(
            self.table_name, "PartitionKey eq 'test'")
        # Assert
        self.assertEqual(len(resp), 2)
        self.assertEqual(resp[0].Description, u'ꀕ')
        self.assertEqual(resp[1].Description, u'ꀕ')

    @record
    def test_unicode_property_name(self):
        # Act
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {'PartitionKey': 'test', 'RowKey': 'test1', u'啊齄丂狛狜': u'ꀕ'})
        self.ts.insert_entity(
            self.table_name,
            {'PartitionKey': 'test', 'RowKey': 'test2', u'啊齄丂狛狜': 'hello'})
        resp = self.ts.query_entities(
            self.table_name, "PartitionKey eq 'test'")
        # Assert
        self.assertEqual(len(resp), 2)
        self.assertEqual(resp[0][u'啊齄丂狛狜'], u'ꀕ')
        self.assertEqual(resp[1][u'啊齄丂狛狜'], u'hello')

    @record
    def test_unicode_create_table_unicode_name(self):
        # Arrange
        self.table_name = self.table_name + u'啊齄丂狛狜'

        # Act
        with self.assertRaises(AzureHttpError):
            # not supported - table name must be alphanumeric, lowercase
            self.ts.create_table(self.table_name)

        # Assert

    @record
    def test_empty_and_spaces_property_value(self):
        # Act
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'EmptyByte': '',
                'EmptyUnicode': u'',
                'SpacesOnlyByte': '   ',
                'SpacesOnlyUnicode': u'   ',
                'SpacesBeforeByte': '   Text',
                'SpacesBeforeUnicode': u'   Text',
                'SpacesAfterByte': 'Text   ',
                'SpacesAfterUnicode': u'Text   ',
                'SpacesBeforeAndAfterByte': '   Text   ',
                'SpacesBeforeAndAfterUnicode': u'   Text   ',
            })
        resp = self.ts.get_entity(self.table_name, 'test', 'test1')
        
        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(resp.EmptyByte, '')
        self.assertEqual(resp.EmptyUnicode, u'')
        self.assertEqual(resp.SpacesOnlyByte, '   ')
        self.assertEqual(resp.SpacesOnlyUnicode, u'   ')
        self.assertEqual(resp.SpacesBeforeByte, '   Text')
        self.assertEqual(resp.SpacesBeforeUnicode, u'   Text')
        self.assertEqual(resp.SpacesAfterByte, 'Text   ')
        self.assertEqual(resp.SpacesAfterUnicode, u'Text   ')
        self.assertEqual(resp.SpacesBeforeAndAfterByte, '   Text   ')
        self.assertEqual(resp.SpacesBeforeAndAfterUnicode, u'   Text   ')

    @record
    def test_none_property_value(self):
        # Act
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'NoneValue': None,
            })
        resp = self.ts.get_entity(self.table_name, 'test', 'test1')

        # Assert
        self.assertIsNotNone(resp)
        self.assertFalse(hasattr(resp, 'NoneValue'))

    @record
    def test_binary_property_value(self):
        # Act
        binary_data = b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n'
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'binary': EntityProperty(EdmType.BINARY, binary_data)
            })
        resp = self.ts.get_entity(self.table_name, 'test', 'test1')

        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(resp.binary.type, EdmType.BINARY)
        self.assertEqual(resp.binary.value, binary_data)

    @record
    def test_timezone(self):
        # Act
        local_tz = tzoffset('BRST', -10800)
        local_date = datetime(2003, 9, 27, 9, 52, 43, tzinfo=local_tz)
        self._create_table(self.table_name)
        self.ts.insert_entity(
            self.table_name,
            {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'date': local_date,
            })
        resp = self.ts.get_entity(self.table_name, 'test', 'test1')

        # Assert
        self.assertIsNotNone(resp)
        self.assertEqual(resp.date, local_date.astimezone(tzutc()))
        self.assertEqual(resp.date.astimezone(local_tz), local_date)

    @record
    def test_locale(self):
        # Arrange
        culture = 'es_ES.utf8' if not os.name is "nt" else "Spanish_Spain"
        locale.setlocale(locale.LC_ALL, culture)
        e = None

        # Act
        try:
            resp = self.ts.query_tables()
        except:
            e = sys.exc_info()[0]

        # Assert
        self.assertIsNone(e)

    @record
    def test_sas_query(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)
        token = self.ts.generate_shared_access_signature(
            self.table_name,
            self._get_shared_access_policy(TableSharedAccessPermissions.QUERY),
        )

        # Act
        service = TableService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        resp = self.ts.query_entities(self.table_name, None, 'age,sex')

        # Assert
        self.assertEqual(len(resp), 2)
        self.assertEqual(resp[0].age, 39)
        self.assertEqual(resp[0].sex, 'male')
        self.assertFalse(hasattr(resp[0], "birthday"))
        self.assertFalse(hasattr(resp[0], "married"))
        self.assertFalse(hasattr(resp[0], "deceased"))

    @record
    def test_sas_add(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        self._create_table(self.table_name)
        policy = self._get_shared_access_policy(TableSharedAccessPermissions.ADD)
        token = self.ts.generate_shared_access_signature(self.table_name, policy)

        # Act
        service = TableService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        service.insert_entity(
            self.table_name,
            {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'text': 'hello',
            })

        # Assert
        resp = self.ts.get_entity(self.table_name, 'test', 'test1')
        self.assertIsNotNone(resp)
        self.assertEqual(resp.text, 'hello')

    @record
    def test_sas_add_inside_range(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        self._create_table(self.table_name)
        policy = self._get_shared_access_policy(TableSharedAccessPermissions.ADD)
        policy.access_policy.start_pk = 'test'
        policy.access_policy.end_pk = 'test'
        policy.access_policy.start_rk = 'test1'
        policy.access_policy.end_rk = 'test1'
        token = self.ts.generate_shared_access_signature(self.table_name, policy)

        # Act
        service = TableService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        service.insert_entity(
            self.table_name,
            {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'text': 'hello',
            })

        # Assert
        resp = self.ts.get_entity(self.table_name, 'test', 'test1')
        self.assertIsNotNone(resp)
        self.assertEqual(resp.text, 'hello')

    @record
    def test_sas_add_outside_range(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        self._create_table(self.table_name)
        policy = self._get_shared_access_policy(TableSharedAccessPermissions.ADD)
        policy.access_policy.start_pk = 'test'
        policy.access_policy.end_pk = 'test'
        policy.access_policy.start_rk = 'test1'
        policy.access_policy.end_rk = 'test1'
        token = self.ts.generate_shared_access_signature(self.table_name, policy)

        # Act
        service = TableService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        with self.assertRaises(AzureHttpError):
            service.insert_entity(
                self.table_name,
                {
                    'PartitionKey': 'test',
                    'RowKey': 'test2',
                    'text': 'hello',
                })

        # Assert

    @record
    def test_sas_update(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)
        policy = self._get_shared_access_policy(TableSharedAccessPermissions.UPDATE)
        token = self.ts.generate_shared_access_signature(self.table_name, policy)

        # Act
        service = TableService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        updated_entity = self._create_updated_entity_dict('MyPartition', '1')
        resp = service.update_entity(self.table_name, updated_entity)

        # Assert
        received_entity = self.ts.get_entity(self.table_name, 'MyPartition', '1')
        self._assert_updated_entity(received_entity)

    @record
    def test_sas_delete(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)
        policy = self._get_shared_access_policy(TableSharedAccessPermissions.DELETE)
        token = self.ts.generate_shared_access_signature(self.table_name, policy)

        # Act
        service = TableService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        service.delete_entity(self.table_name, 'MyPartition', '1')

        # Assert
        with self.assertRaises(AzureMissingResourceHttpError):
            self.ts.get_entity(self.table_name, 'MyPartition', '1')

    @record
    def test_sas_signed_identifier(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        self._create_table_with_default_entities(self.table_name, 2)

        si = SignedIdentifier()
        si.id = 'testid'
        si.access_policy.start = '2011-10-11'
        si.access_policy.expiry = '2018-10-12'
        si.access_policy.permission = TableSharedAccessPermissions.QUERY
        identifiers = SignedIdentifiers()
        identifiers.signed_identifiers.append(si)

        resp = self.ts.set_table_acl(self.table_name, identifiers)

        token = self.ts.generate_shared_access_signature(
            self.table_name,
            SharedAccessPolicy(signed_identifier=si.id),
        )

        # Act
        service = TableService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        resp = self.ts.query_entities(self.table_name, None, 'age,sex')

        # Assert
        self.assertEqual(len(resp), 2)
        self.assertEqual(resp[0].age, 39)
        self.assertEqual(resp[0].sex, 'male')
        self.assertFalse(hasattr(resp[0], "birthday"))
        self.assertFalse(hasattr(resp[0], "married"))
        self.assertFalse(hasattr(resp[0], "deceased"))

    @record
    def test_get_table_acl(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        acl = self.ts.get_table_acl(self.table_name)

        # Assert
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl.signed_identifiers), 0)

    @record
    def test_get_table_acl_iter(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        acl = self.ts.get_table_acl(self.table_name)
        for signed_identifier in acl:
            pass

        # Assert
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl.signed_identifiers), 0)
        self.assertEqual(len(acl), 0)

    @record
    def test_get_table_acl_with_non_existing_container(self):
        # Arrange

        # Act
        with self.assertRaises(AzureMissingResourceHttpError):
            self.ts.get_table_acl(self.table_name)

        # Assert

    @record
    def test_set_table_acl(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        resp = self.ts.set_table_acl(self.table_name)

        # Assert
        self.assertIsNone(resp)
        acl = self.ts.get_table_acl(self.table_name)
        self.assertIsNotNone(acl)

    @record
    def test_set_table_acl_with_empty_signed_identifiers(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        identifiers = SignedIdentifiers()

        resp = self.ts.set_table_acl(self.table_name, identifiers)

        # Assert
        self.assertIsNone(resp)
        acl = self.ts.get_table_acl(self.table_name)
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl.signed_identifiers), 0)

    @record
    def test_set_table_acl_with_signed_identifiers(self):
        # Arrange
        self._create_table_with_default_entities(self.table_name, 1)

        # Act
        si = SignedIdentifier()
        si.id = 'testid'
        si.access_policy.start = '2011-10-11'
        si.access_policy.expiry = '2011-10-12'
        si.access_policy.permission = TableSharedAccessPermissions.QUERY
        identifiers = SignedIdentifiers()
        identifiers.signed_identifiers.append(si)

        resp = self.ts.set_table_acl(self.table_name, identifiers)

        # Assert
        self.assertIsNone(resp)
        acl = self.ts.get_table_acl(self.table_name)
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl.signed_identifiers), 1)
        self.assertEqual(len(acl), 1)
        self.assertEqual(acl.signed_identifiers[0].id, 'testid')
        self.assertEqual(acl[0].id, 'testid')

    @record
    def test_set_table_acl_with_non_existing_table(self):
        # Arrange

        # Act
        with self.assertRaises(AzureMissingResourceHttpError):
            self.ts.set_table_acl(self.table_name)

        # Assert


#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()
