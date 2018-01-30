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
    '''
    This test checks that if the advertising counter goes above the limit,
    and the user is not a patron, then they should get ads.
    '''
    sources_bak = conftest.clear_parameters()
    core.parameters.add_source({'advertising': {'enable': True}})

    keys_bak = await core.keystore.get('advert_counter', interface.channel.id)
    await core.keystore.set('advert_counter',
                            interface.channel.id,
                            core.parameters.get('advertising interval') + 1)
    patrons.PATRONS = {interface.target.id: patrons.TIER_NONE}

    assert(await advertising.should_advertise_to(interface.target,
                                                 interface.channel))

    patrons.PATRONS = {}
    await core.keystore.set('advert_counter', interface.channel.id, keys_bak)
    conftest.reset_parameters(sources_bak)


# BUG: automata basically doesn't let you use other fixtures
@conftest.automata_test
async def test_increment_adcount(interface):
    '''
    This checks that the advert counter is incremented if the user is not
    a patron.
    '''
    sources_bak = conftest.clear_parameters()
    core.parameters.add_source({'advertising': {'enable': True}})
    starting_count = core.parameters.get('advertising starting-amount')

    await core.keystore.set('advert_counter',
                            interface.channel.id,
                            starting_count)
    patrons.PATRONS = {interface.target.id: patrons.TIER_NONE}

    await advertising.should_advertise_to(interface.target, interface.channel)

    assert await\
        core.keystore.get('advert_counter', interface.channel.id)\
        >\
        starting_count

    patrons.PATRONS = {}
    conftest.reset_parameters(sources_bak)


# BUG: automata basically doesn't let you use other fixtures
@conftest.automata_test
async def test_patron_ads(interface):
    '''
    This checks that patrons do not get ads.
    '''
    sources_bak = conftest.clear_parameters()
    core.parameters.add_source({'advertising': {'enable': True}})
    patrons.PATRONS = {interface.target.id: patrons.TIER_CONSTANT}

    assert(not await advertising.should_advertise_to(interface.target,
                                                     interface.channel))

    patrons.PATRONS = {}
    conftest.reset_parameters(sources_bak)
