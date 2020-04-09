from __future__ import absolute_import, print_function, unicode_literals

import pytest

@pytest.mark.usefixtures("mock_etcd")
def test_frame_create(frame_factory, test_db_cursor):
    pkid = frame_factory("test", description="Just testing")
    assert isinstance(pkid, str)
    test_db_cursor.execute("select * from frame;")
    rec = test_db_cursor.fetchone()
    assert rec["pkid"] == pkid
    assert rec["description"] == "Just testing"
