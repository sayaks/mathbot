import advertising
import core.keystore
import core.parameters
import patrons
import pytest

import conftest

@pytest.mark.asyncio
async def test_no_advertise(parameters):
    '''
    This test checks that ads will not be displayed if the advertising
    key is set to False.
    '''
    parameters.add_source({'advertising': {'enable': False}})
    assert(not await advertising.should_advertise_to(None, None))

# BUG: automata basically doesn't let you use other fixtures
@conftest.automata_test
async def test_advertise(interface):
    sources_bak = core.parameters.sources
    core.parameters.reset()
    core.parameters.add_source({'advertising': {'enable': True}})
    keys_bak = await core.keystore.get('advert_counter', interface.channel.id)
    await core.keystore.set('advert_counter', interface.channel.id, core.parameters.get('advertising interval') + 1)
    patrons.PATRONS = {interface.target.id: patrons.TIER_NONE}

    assert(await advertising.should_advertise_to(interface.target, interface.channel))

    # HACK: no good way of doing this as of rn
    patrons.PATRONS = {}
    await core.keystore.set('advert_counter', interface.channel.id, keys_bak)
    core.parameters.reset(False)
    core.parameters.sources = sources_bak

# BUG: automata basically doesn't let you use other fixtures
@conftest.automata_test
async def test_increment_adcount(interface):
    sources_bak = core.parameters.sources
    starting_count = core.parameters.get('advertising starting-amount')
    core.parameters.reset()
    core.parameters.add_source({'advertising': {'enable': True}})
    await core.keystore.set('advert_counter',
                            interface.channel.id,
                            starting_count)
    patrons.PATRONS = {interface.target.id: patrons.TIER_NONE}

    await advertising.should_advertise_to(interface.target, interface.channel)

    assert(await core.keystore.get('advert_counter', interface.channel.id) > starting_count)

    # HACK: no good way of doing this as of rn
    patrons.PATRONS = {}
    core.parameters.reset(False)
    core.parameters.sources = sources_bak

# BUG: automata basically doesn't let you use other fixtures
@conftest.automata_test
async def test_patron_ads(interface):
    patrons.PATRONS = {interface.target.id: patrons.TIER_CONSTANT}
    assert(not await advertising.should_advertise_to(interface.target, interface.channel))
