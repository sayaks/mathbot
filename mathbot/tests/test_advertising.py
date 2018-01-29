import advertising
import automata
import core.parameters
import core.keystore
import patrons
import pytest

import conftest

async def test_no_advertise():
    '''
    This test checks that ads will not be displayed if the advertising
    key is set to False.
    '''
    sources_bak = core.parameters.sources
    core.parameters.reset()
    core.parameters.add_source({'advertising': {'enable': False}})

    assert(not await advertising.should_advertise_to(0, 0))

    # HACK: there isn't an idiomatic way of doing this yet
    core.parameters.reset(False)
    core.parameters.sources = sources_bak


@conftest.automata_test
async def test_advertise(interface):
    sources_bak = core.parameters.sources
    core.parameters.reset()
    core.parameters.add_source({'advertising': {'enable': True}})
    core.keystore.set('advert_counter', interface.channel, core.parameters.get('advertising interval') + 1)
    patrons.PATRONS = {interface.client: patrons.TIER_NONE}

    assert(await advertising.should_advertise_to(interface.client, interface.channel))

    # HACK: there isn't an idiomatic way of doing this yet
    core.parameters.reset(False)
    core.parameters.sources = sources_bak
    patrons.PATRONS = {}
