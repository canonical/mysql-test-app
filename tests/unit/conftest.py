# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from ops import testing

from charm import MySQLTestApplication
from literals import PEER


@pytest.fixture
def charm():
    """Provide a charm instance with a peer relation via testing.Context."""
    ctx = testing.Context(MySQLTestApplication)
    peer_relation = testing.PeerRelation(endpoint=PEER)
    state_in = testing.State(relations={peer_relation})
    with ctx(ctx.on.update_status(), state_in) as manager:
        yield manager.charm
