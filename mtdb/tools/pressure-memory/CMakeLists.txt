CMAKE_MINIMUM_REQUIRED (VERSION 2.8 FATAL_ERROR)

SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Werror")

# http://stackoverflow.com/questions/7724569/debug-vs-release-in-cmake
# cmake -DCMAKE_BUILD_TYPE=Debug

# C++11
if (UNIX)
	SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=gnu++0x")
endif()

FIND_PACKAGE( Boost
	COMPONENTS system timer REQUIRED )

INCLUDE_DIRECTORIES(${Boost_INCLUDE_DIRS})
ADD_EXECUTABLE ( pressure-memory main.cpp util.cpp )
TARGET_LINK_LIBRARIES ( pressure-memory ${Boost_LIBRARIES} )
