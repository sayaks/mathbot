import advertising
import core.keystore
import patrons
import pytest

import conftest

@pytest.fixture(scope = 'function')
def parameters():
    import core.parameters
    sources_bak = core.parameters.sources
    core.parameters.reset()
    yield core.parameters

    # HACK: there isn't an idiomatic way of doing this yet    
    core.parameters.reset(False)
    core.parameters.sources = sources_bak

async def test_no_advertise(parameters):
    '''
    This test checks that ads will not be displayed if the advertising
    key is set to False.
    '''
    parameters.add_source({'advertising': {'enable': False}})
    assert(not await advertising.should_advertise_to(0, 0))


@conftest.automata_test
async def test_advertise(interface, parameters):
    parameters.add_source({'advertising': {'enable': True}})
    core.keystore.set('advert_counter', interface.channel, core.parameters.get('advertising interval') + 1)
    patrons.PATRONS = {interface.client: patrons.TIER_NONE}

    assert(await advertising.should_advertise_to(interface.client, interface.channel))

    # HACK: no good way of doing this as of rn
    patrons.PATRONS = {}
