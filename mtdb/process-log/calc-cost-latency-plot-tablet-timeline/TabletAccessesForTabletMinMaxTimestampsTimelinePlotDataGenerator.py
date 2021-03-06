import datetime
import math
import os
import sys

sys.path.insert(0, "../../util/python")
import Cons
import Util

import CassLogReader
import Desc
import Event
import SimTime
import TabletMinMaxTimestampsTimelinePlotDataGenerator

_fn_plot_data = None

_id_events = {}

def Gen():
	with Cons.MeasureTime("Generating tablet accesses plot data for min/max timestamps plot ..."):
		for l in CassLogReader._logs:
			_BuildIdEventsMap(l)
		NumToTime.SetNumAccessesTimeRatio()
		_WriteToFile()


class Events:
	def __init__(self):
		self.time_cnts = {}

	def AddAccStat(self, simulated_time, tablet_acc_stat):
		# tablet_acc_stat is of type AccessStat.AccStat
		self.time_cnts[simulated_time] = tablet_acc_stat

	def __str__(self):
		return "Events: " + ", ".join("%s: %s" % item for item in vars(self).items())


def _BuildIdEventsMap(e):
	if type(e.event) is not Event.AccessStat:
		return
	for e1 in e.event.entries:
		if type(e1) is Event.AccessStat.MemtAccStat:
			# We don't plot memtables for now.
			pass
		elif type(e1) is Event.AccessStat.SstAccStat:
			sst_gen = e1.id_
			if TabletMinMaxTimestampsTimelinePlotDataGenerator.SstExist(sst_gen):
				global _id_events
				if sst_gen not in _id_events:
					_id_events[sst_gen] = Events()
				_id_events[sst_gen].AddAccStat(e.simulated_time, e1)
				#Cons.P("%s %s" % (e.simulated_time, e1))


class NumToTime:
	max_num_bf_positives_per_day = 0
	min_timestamp_range = None
	# in seconds, in float
	timedur_per_access = None

	# To skip plotting
	datetime_out_of_rage = "090101-000000.000000"

	# Number of accesses is the sum of true and false positives, both of which
	# access the SSTable.
	@staticmethod
	def _SetMaxNumAccesses():
		global _id_events
		for sstgen, events in sorted(_id_events.iteritems()):
			time_prev = None
			num_needto_read_datafile_prev = 0
			for time_, cnts in sorted(events.time_cnts.iteritems()):
				if time_prev == None:
					# We ignore the first time window, i.e., we don't print anything for
					# it. There is a very small time window between the first access and
					# it is logged.
					pass
				else:
					if time_ == time_prev:
						# It may happen.
						raise RuntimeError("Unexpected: time_(%s) == time_prev" % time_)
					time_dur_days = (time_ - time_prev).total_seconds() / (24.0 * 3600)
					num_needto_read_datafile_per_day = (cnts.num_needto_read_datafile - num_needto_read_datafile_prev) / time_dur_days
					#Cons.P("%02d %20s %10d %10.6f %13.6f"
					#		% (sstgen
					#			, time_.strftime("%y%m%d-%H%M%S.%f")
					#			, cnts.num_needto_read_datafile - num_needto_read_datafile_prev
					#			, time_dur_days
					#			, num_needto_read_datafile_per_day))
					NumToTime.max_num_bf_positives_per_day = max(NumToTime.max_num_bf_positives_per_day, num_needto_read_datafile_per_day)
				time_prev = time_
				num_needto_read_datafile_prev = cnts.num_needto_read_datafile
		Cons.P("NumToTime.max_num_bf_positives_per_day: %f" % NumToTime.max_num_bf_positives_per_day)

	@staticmethod
	def _SetMinTabletTimestampRange():
		for sstgen, v in sorted(TabletMinMaxTimestampsTimelinePlotDataGenerator._id_events.iteritems()):
			if NumToTime.min_timestamp_range == None:
				NumToTime.min_timestamp_range = v.TimestampRange()
			else:
				NumToTime.min_timestamp_range = min(NumToTime.min_timestamp_range, v.TimestampRange())
		Cons.P("NumToTime.min_timestamp_range: %s" % NumToTime.min_timestamp_range)

	@staticmethod
	def SetNumAccessesTimeRatio():
		NumToTime._SetMaxNumAccesses()
		NumToTime._SetMinTabletTimestampRange()
		NumToTime.timedur_per_access = NumToTime.min_timestamp_range.total_seconds() / NumToTime.max_num_bf_positives_per_day

	@staticmethod
	def Conv(base_time, cnt):
		if cnt == 0:
			return NumToTime.datetime_out_of_rage
		else:
			return (base_time + datetime.timedelta(seconds = (NumToTime.timedur_per_access * cnt))).strftime("%y%m%d-%H%M%S.%f")

	@staticmethod
	def ConvLogscale(base_time, cnt):
		try:
			if cnt == 0:
				return NumToTime.datetime_out_of_rage
			else:
				return (base_time + datetime.timedelta(seconds = (NumToTime.min_timestamp_range.total_seconds()
					* math.log(cnt + 1) / math.log(NumToTime.max_num_bf_positives_per_day + 1)))).strftime("%y%m%d-%H%M%S.%f")
		except ValueError as e:
			Cons.P("%s: cnt=%d NumToTime.max_num_bf_positives_per_day=%d"
					% (e, cnt, NumToTime.max_num_bf_positives_per_day))
			raise


def _WriteToFile():
	global _fn_plot_data
	_fn_plot_data = os.path.dirname(__file__) \
			+ "/plot-data/" + Desc.ExpDatetime() + "-tablet-accesses-for-min-max-timestamp-plot-by-time"
	with open(_fn_plot_data, "w") as fo:
		fmt = "%2s %20s %20s" \
				" %10d %10d %10d" \
				" %10d %10d" \
				" %20s"
		fo.write("%s\n" % Util.BuildHeader(fmt,
			"id(sst_gen) simulated_time y_cord_base(min_timestamp)"
			" num_reads_per_day num_needto_read_datafile_per_day num_bf_negatives_per_day"
			" num_num_true_positives_per_day(not_complete) num_false_positives_per_day(not_complete)"
			" num_bf_positivies_per_day_converted_to_time"))
		for id_, v in sorted(_id_events.iteritems()):
			time_prev = None
			num_reads_prev = 0
			num_needto_read_datafile_prev = 0
			num_negatives_prev = 0
			# These two are not complete numbers. They are not always tracked.
			num_tp_prev = 0
			num_fp_prev = 0
			min_timestamp = TabletMinMaxTimestampsTimelinePlotDataGenerator.GetTabletMinTimestamp(id_)
			for time_, cnts in sorted(v.time_cnts.iteritems()):
				if time_ > SimTime.SimulatedTimeEnd():
					continue

				num_negatives = cnts.num_reads - cnts.num_needto_read_datafile
				if time_prev == None:
					# We ignore the first time window, i.e., we don't print anything for
					# it. There is a very small time window between the first access and
					# it is logged.
					pass
				else:
					if time_ == time_prev:
						# It may happen.
						raise RuntimeError("Unexpected: time_(%s) == time_prev" % time_)
					time_dur_days = (time_ - time_prev).total_seconds() / (24.0 * 3600)
					num_needto_read_datafile_per_day = (cnts.num_needto_read_datafile - num_needto_read_datafile_prev) / time_dur_days
					if cnts.num_needto_read_datafile < num_needto_read_datafile_prev:
						num_needto_read_datafile_per_day = 0
						# This can happen when multiple threads create SSTable access stat instances simultaneously.
						Cons.P("BF positives decreases and ignored: %20s %d %d %f"
								% (time_.strftime("%y%m%d-%H%M%S.%f")
									, num_needto_read_datafile_prev
									, cnts.num_needto_read_datafile
									, time_dur_days
									))
					fo.write((fmt + "\n") % (id_
						, time_.strftime("%y%m%d-%H%M%S.%f")
						, min_timestamp.strftime("%y%m%d-%H%M%S.%f")
						, (cnts.num_reads - num_reads_prev) / time_dur_days
						, num_needto_read_datafile_per_day
						, (num_negatives - num_negatives_prev) / time_dur_days
						, (cnts.num_tp - num_tp_prev) / time_dur_days
						, (cnts.num_fp - num_fp_prev) / time_dur_days
						, NumToTime.Conv(min_timestamp, num_needto_read_datafile_per_day)
						))
				time_prev = time_
				num_reads_prev = cnts.num_reads
				num_needto_read_datafile_prev = cnts.num_needto_read_datafile
				num_negatives_prev = num_negatives
				num_tp_prev = cnts.num_tp
				num_fp_prev = cnts.num_fp
			fo.write("\n")
	Cons.P("Created file %s %d" % (_fn_plot_data, os.path.getsize(_fn_plot_data)))
