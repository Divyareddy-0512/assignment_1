import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner


MASK32 = 0xFFFFFFFF


def prbs_next(state, mode):
    state &= MASK32

    if mode == 0:
        feedback = ((((state >> 1) & 0x1F) ^ (state & 0x1F)) << 3)
        feedback |= (((state >> 6) ^ (state >> 5) ^ state) & 0x1) << 2
        feedback |= (((state >> 6) ^ (state >> 4)) & 0x1) << 1
        feedback |= ((state >> 5) ^ (state >> 3)) & 0x1
    elif mode == 1:
        feedback = ((state >> 7) & 0xFF) ^ ((state >> 6) & 0xFF)
    elif mode == 2:
        feedback = ((state >> 15) & 0xFF) ^ ((state >> 10) & 0xFF)
    elif mode == 3:
        feedback = ((state >> 23) & 0xFF) ^ ((state >> 20) & 0xFF)
    else:
        return state

    return (((state & 0xFFFFFF) << 8) | feedback) & MASK32


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.enable.value = 0
    dut.load.value = 0
    dut.prbs_type.value = 0
    dut.seed.value = 0

    await Timer(20, unit="ns")

    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def load_seed(dut, seed):
    dut.seed.value = seed
    dut.load.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    dut.load.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_reset(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    assert dut.prbs_out.value == 0, \
        f"Reset failed. Expected 0 Got {dut.prbs_out.value}"


@cocotb.test()
async def test_seed_load(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    seed = 0x12345679
    await load_seed(dut, seed)

    expected = seed & 0xFF

    assert dut.prbs_out.value == expected, \
        f"Seed load failed. Expected {hex(expected)} Got {hex(int(dut.prbs_out.value))}"


@cocotb.test()
async def test_load_only_on_posedge(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    first_seed = 0x12345679
    second_seed = 0xABCDEF13

    dut.seed.value = first_seed
    dut.load.value = 1

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    assert int(dut.prbs_out.value) == (first_seed & 0xFF), \
        "Seed was not loaded on the first asserted load cycle"

    dut.seed.value = second_seed

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    assert int(dut.prbs_out.value) == (first_seed & 0xFF), \
        "Seed reloaded while load stayed high; expected load to be edge-detected"

    dut.load.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    dut.load.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    assert int(dut.prbs_out.value) == (second_seed & 0xFF), \
        "Seed did not reload after load was deasserted and asserted again"


@cocotb.test()
async def test_hold_when_disabled(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    await load_seed(dut, 0xABCDEF13)

    value_before = int(dut.prbs_out.value)

    dut.enable.value = 0

    for _ in range(6):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

    value_after = int(dut.prbs_out.value)

    assert value_before == value_after, \
        "Output changed when disabled (enable=0)"


@cocotb.test()
async def test_prbs_modes(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    seed = 0xDEADBEF0

    for mode in [0, 1, 2, 3]:
        await reset_dut(dut)
        await load_seed(dut, seed)

        dut.prbs_type.value = mode
        dut.enable.value = 1

        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

        expected = prbs_next(seed, mode) & 0xFF
        actual = int(dut.prbs_out.value)

        assert actual == expected, \
            f"PRBS mode {mode} mismatch. Expected {hex(expected)} Got {hex(actual)}"


@cocotb.test()
async def test_multiple_cycles(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    seed = 0xCAFEBABF
    await load_seed(dut, seed)

    dut.enable.value = 1
    dut.prbs_type.value = 1

    outputs = []
    expected_outputs = []
    state = seed

    for _ in range(8):
        state = prbs_next(state, 1)
        expected_outputs.append(state & 0xFF)

        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        outputs.append(int(dut.prbs_out.value))

    assert outputs == expected_outputs, \
        f"PRBS output sequence mismatch. Expected {[hex(v) for v in expected_outputs]} Got {[hex(v) for v in outputs]}"

def test_simple_dff_hidden_runner():
   sim = os.getenv("SIM", "icarus")

   proj_path = Path(__file__).resolve().parent.parent

   sources = [proj_path / "source/prbs_generator_8bit.sv"]

   runner = get_runner(sim)
   runner.build(
       sources=sources,
       hdl_toplevel="prbs_generator_8bit",
       always=True,
   )

   runner.test(hdl_toplevel="prbs_generator_8bit", test_module="test_prbs_generator_8bit_hidden")
