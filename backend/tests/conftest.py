import pytest
import sys
from unittest.mock import MagicMock

# 1. Create a global mock client structure
mock_client = MagicMock()
mock_table = MagicMock()
mock_client.table.return_value = mock_table

mock_select = MagicMock()
mock_table.select.return_value = mock_select

mock_eq = MagicMock()
mock_select.eq.return_value = mock_eq

mock_upsert = MagicMock()
mock_table.upsert.return_value = mock_upsert

mock_insert = MagicMock()
mock_table.insert.return_value = mock_insert

mock_update = MagicMock()
mock_table.update.return_value = mock_update

mock_execute = MagicMock()
mock_execute.data = []
mock_execute.error = None

mock_select.execute.return_value = mock_execute
mock_eq.execute.return_value = mock_execute
mock_upsert.execute.return_value = mock_execute
mock_insert.execute.return_value = mock_execute
mock_update.execute.return_value = mock_execute

mock_rpc = MagicMock()
mock_client.rpc.return_value = mock_rpc
mock_rpc.execute.return_value = mock_execute

# 2. Globally intercept and patch supabase.create_client before any other modules load
import supabase
supabase.create_client = MagicMock(return_value=mock_client)

@pytest.fixture(autouse=True)
def mock_supabase():
    """
    Fixture that resets mock return values between test cases.
    """
    # Reset default return states
    mock_execute.data = []
    mock_execute.error = None
    
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.execute.return_value = mock_execute
    
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = mock_execute
    
    mock_table.upsert.return_value = mock_upsert
    mock_upsert.execute.return_value = mock_execute
    
    mock_table.update.return_value = mock_update
    mock_update.execute.return_value = mock_execute
    
    mock_client.rpc.return_value = mock_rpc
    mock_rpc.execute.return_value = mock_execute

    yield {
        "client": mock_client,
        "table": mock_table,
        "select": mock_select,
        "eq": mock_eq,
        "upsert": mock_upsert,
        "insert": mock_insert,
        "update": mock_update,
        "execute": mock_execute,
        "rpc": mock_rpc
    }
