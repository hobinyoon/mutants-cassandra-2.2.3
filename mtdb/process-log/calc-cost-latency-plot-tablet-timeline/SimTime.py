import sys
import datetime

sys.path.insert(0, "../../util/python")
import Cons

_simulation_time_begin = None
_simulation_time_end = None
_simulated_time_begin = None
_simulated_time_end = None
_simulation_time_dur_sec = None
_simulated_time_dur_sec = None

def Init(simulation_time_dur_ms_first,
		simulation_time_begin, simulated_time_begin,
		simulation_time_end, simulated_time_end):
	global _simulation_time_begin
	global _simulation_time_end
	global _simulated_time_begin
	global _simulated_time_end
	global _simulation_time_dur_sec
	global _simulated_time_dur_sec
	_simulation_time_begin = simulation_time_begin
	_simulation_time_end   = simulation_time_end
	_simulated_time_begin  = simulated_time_begin
	_simulated_time_end    = simulated_time_end

	with Cons.MeasureTime("Init SimTime ..."):
		Cons.P("Before adjustment using simulation_time_dur_ms_first:")
		Cons.P("  _simulation_time_begin: %s" % _simulation_time_begin)
		Cons.P("  _simulation_time_end  : %s" % _simulation_time_end)
		Cons.P("  _simulated_time_begin : %s" % _simulated_time_begin)
		Cons.P("  _simulated_time_end   : %s" % _simulated_time_end)
		Cons.P("  simulation_time_dur_ms_first: %d" % simulation_time_dur_ms_first)

		# Adjust _simulation_time_begin based on simulation_time_dur_ms_first
		simulation_time_begin_adjusted = _simulation_time_begin \
				- datetime.timedelta(microseconds = (simulation_time_dur_ms_first * 1000))
		#
		# _simulation_time_end - simulation_time_begin_adjusted : _simulation_time_begin - _simulation_time_end
		# = _simulated_time_end - simulated_time_begin_adjusted : _simulated_time_begin - _simulated_time_end
		#
		# _simulated_time_end - simulated_time_begin_adjusted
		# = (_simulation_time_end - simulation_time_begin_adjusted)
		#   * (_simulated_time_begin - _simulated_time_end)
		#   / (_simulation_time_begin - _simulation_time_end)
		#
		simulated_time_begin_adjusted = _simulated_time_end - \
				datetime.timedelta(seconds = \
					((_simulation_time_end - simulation_time_begin_adjusted).total_seconds() \
					* (_simulated_time_begin - _simulated_time_end).total_seconds() \
					/ (_simulation_time_begin - _simulation_time_end).total_seconds()))
		# simulated_time_begin_adjusted is like 34 mins from the configured begin
		# time. Not sure where the delay comes from. Don't think it's a big deal
		# for now.
		_simulation_time_begin = simulation_time_begin_adjusted
		_simulated_time_begin  = simulated_time_begin_adjusted
		_simulation_time_dur_sec = (_simulation_time_end - _simulation_time_begin).total_seconds()
		_simulated_time_dur_sec = (_simulated_time_end - _simulated_time_begin).total_seconds()
		Cons.P("After adjustment:")
		Cons.P("  _simulation_time_begin: %s" % _simulation_time_begin)
		Cons.P("  _simulation_time_end  : %s" % _simulation_time_end)
		Cons.P("  _simulated_time_begin : %s" % _simulated_time_begin)
		Cons.P("  _simulated_time_end   : %s" % _simulated_time_end)
		Cons.P("  simulation time dur: %f secs" % _simulation_time_dur_sec)
		Cons.P("  simulated time dur: %.f secs, %s, %f years"
				% ((_simulated_time_end - _simulated_time_begin).total_seconds()
				, datetime.timedelta(seconds = _simulated_time_dur_sec)
				, _simulated_time_dur_sec / (365.25 * 24 * 3600))
				)


def SimulatedTime(simulation_time):
	return _simulated_time_end - \
			datetime.timedelta(seconds = \
			((_simulation_time_end - simulation_time).total_seconds() \
			* (_simulated_time_begin - _simulated_time_end).total_seconds() \
			/ (_simulation_time_begin - _simulation_time_end).total_seconds()))


def SimulatedTimeBegin():
	return _simulated_time_begin


def SimulatedTimeEnd():
	return _simulated_time_end


def SimulationTimeEnd():
	return _simulation_time_end


def StrftimeWithOutofrange(d):
	if d == None:
		return "090101-000000.000000"
	else:
		return d.simulated_time.strftime("%y%m%d-%H%M%S.%f")
