#include <string.h>
#include <stdio.h>
#include <unistd.h>

#include <algorithm>
#include <iostream>
#include <regex>
#include <boost/algorithm/string.hpp>
#include <boost/format.hpp>
#include "conf.h"
#include "util.h"

using namespace std;

// Cached memory size in mb
void GetFreeAndCachedMemorySizeMb(int& free, int& cached) {
	free = cached = 0;

	string lines = Util::exec("free -mt");
	//              total       used       free     shared    buffers     cached
	// Mem:         11991      11576        415         16        116      10938
	// -/+ buffers/cache:        521      11469
	// Swap:            0          0          0
	// Total:       11991      11576        415

	// TODO: think about what to do with swap. better disable.
	stringstream ss(lines);
	regex rgx("^Mem:\\s+\\d+\\s+\\d+\\s+\\d+\\s+\\d+\\s+\\d+\\s+\\d+");

	string line;
	const auto sep = boost::is_any_of(" ");
	while (getline(ss, line, '\n')) {
		//cout << boost::format("[%s]\n") % line;
		smatch match;
		if (regex_search(line, match, rgx)) {
			vector<string> tokens;
			boost::split(tokens, line, sep, boost::token_compress_on);
			if (tokens.size() != 7)
				throw runtime_error(str(boost::format("Unexpected format [%s]") % line));
			free = atoi(tokens[3].c_str());
			cached = atoi(tokens[6].c_str());
			return;
		}
	}

	throw runtime_error(str(boost::format("Unexpected format [%s]") % lines));
}


// A child process is pre-created and serves memory pressure requests. Parent
// process is free to call fork() without having to worry about duplicating the
// child process's memory.
class MemPressurer {
private:
	// pipefd[0] refers to the read end of the pipe. pipefd[1] refers to the
	// write end of the pipe.
	// Parent-to-child and child-to-parent pipes
	int pipe_pc[2];
	int pipe_cp[2];
	vector<char*> allocated_mem;

	// Child process
	void _ServeRequests() {
		while (true) {
			char cmd;
			Util::readn(pipe_pc[0], &cmd, sizeof(cmd));
			if (cmd == 'a') {
				int to_alloc_mb;
				Util::readn(pipe_pc[0], &to_alloc_mb, sizeof(to_alloc_mb));

				boost::timer::cpu_timer timer;
				int allocated = 0;
				for (int i = 0; i < (to_alloc_mb / Conf::mem_alloc_chunk_mb); i ++) {
					char* c = new (nothrow) char[Conf::mem_alloc_chunk_mb * 1024 * 1024];
					if (c == NULL) {
						cout << boost::format("Could not allocate. i=%d\n") % i;
						break;
					}
					// It works with just initializing the memory, without
					// randomization. The kernel doesn't have compressed memory on.
					memset(c, 0, Conf::mem_alloc_chunk_mb * 1024 * 1024);
					allocated_mem.push_back(c);
					allocated += Conf::mem_alloc_chunk_mb;
				}
				//cout << boost::format("C: Allocated %d MB of memory in %f sec\n")
				//	% allocated % (timer.elapsed().wall / 1000000000.0);
				cout << boost::format("a:%d ") % allocated << flush;
			} else if (cmd == 'f') {
				int to_free_mb;
				Util::readn(pipe_pc[0], &to_free_mb, sizeof(to_free_mb));

				boost::timer::cpu_timer timer;
				int freed = 0;
				for (int i = 0; i < (to_free_mb / Conf::mem_alloc_chunk_mb); i ++) {
					if (allocated_mem.size() == 0)
						break;
					char* c = allocated_mem.back();
					allocated_mem.pop_back();
					delete[] c;
					freed += Conf::mem_alloc_chunk_mb;
				}
				//cout << boost::format("C: Freed %d MB of memory in %f sec\n")
				//	% freed % (timer.elapsed().wall / 1000000000.0);
				cout << boost::format("f:%d ") % freed << flush;
			} else {
				throw runtime_error(str(boost::format("Unexpected cmd=[%c]") % cmd));
			}

			// Done
			char response = 'd';
			Util::writen(pipe_cp[1], &response, sizeof(response));
		}
	}

	void _PipeAndFork() {
		if (pipe(pipe_pc) == -1)
			throw runtime_error(str(boost::format("pipe() failed: errno=%d") % errno));
		if (pipe(pipe_cp) == -1)
			throw runtime_error(str(boost::format("pipe() failed: errno=%d") % errno));

		pid_t pid = fork();
		if (pid == 0) {
			// Child. Close unused ends.
			close(pipe_pc[1]);
			close(pipe_cp[0]);
			_ServeRequests();
		} else if (pid < 0) {
			throw runtime_error(str(boost::format("fork() failed: errno=%d") % errno));
		} else {
			// Parent. Close unused ends.
			close(pipe_pc[0]);
			close(pipe_cp[1]);
		}
	}

public:
	MemPressurer() {
		_PipeAndFork();
	}

	// These two are called by parent

	void AllocMemory(int to_alloc_mb) {
		const char cmd = 'a';
		Util::writen(pipe_pc[1], &cmd, sizeof(cmd));
		Util::writen(pipe_pc[1], &to_alloc_mb, sizeof(int));

		char response;
		Util::readn(pipe_cp[0], &response, sizeof(response));
		if (response != 'd')
			throw runtime_error(str(boost::format("Unexpected response [%c]") % response));
	}

	void FreeMemory(int to_free_mb) {
		const char cmd = 'f';
		Util::writen(pipe_pc[1], &cmd, sizeof(cmd));
		Util::writen(pipe_pc[1], &to_free_mb, sizeof(int));

		char response;
		Util::readn(pipe_cp[0], &response, sizeof(response));
		if (response != 'd')
			throw runtime_error(str(boost::format("Unexpected response [%c]") % response));
	}
};


void _SleepABit() {
	// Sleep for a while when memory size has changed.
	struct timespec req;
	req.tv_sec = 0;
	req.tv_nsec = Conf::sleep_nsec;
	nanosleep(&req, NULL);
}


int main() {
	MemPressurer mp;

	while (true) {
		int free, cached;
		try {
			GetFreeAndCachedMemorySizeMb(free, cached);
			// cout << boost::format("S: %d, %d\n") % free % cached;
		} catch (const Util::ErrorNoMem& e) {
			cout << "S: ErrorNoMem\n";
			exit(-1);
		}

		// Careful not to trigger OOM killer. If the free memory is too small, no
		// more allocation.
		if (free < Conf::free_lower_bound_mb) {
			_SleepABit();
			continue;
		}

		// When cached is higher than the threshold, pressure memory.
		// When cached is no higher than the threshold, release memory to meet
		// free_memory_target.
		bool pressure_size_changed = false;
		int to_alloc_mb = ((cached - Conf::cached_memory_target_mb) / Conf::mem_alloc_chunk_mb) * Conf::mem_alloc_chunk_mb;
		if (to_alloc_mb > 0) {
			// Allocate little by little
			mp.AllocMemory(Conf::mem_alloc_chunk_mb);
			pressure_size_changed = true;
		} else {
			int to_free_mb = ((Conf::free_memory_target_mb - free) / Conf::mem_alloc_chunk_mb) * Conf::mem_alloc_chunk_mb;
			if (to_free_mb > 0) {
				mp.FreeMemory(to_free_mb);
				pressure_size_changed = true;
			}
		}

		if (! pressure_size_changed)
			_SleepABit();
	}

	// TODO: Keep the cached memory size to proportional to the shrinked heap size
	// c3.2xlarge has 15 GB of memory.
	// @ Measure the heap memory size of unmodified Cassandra and cached size.
	// Should have a better idea then.

	return 0;
}