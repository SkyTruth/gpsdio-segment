==============
gpsdio-segment
==============

https://github.com/GlobalFishingWatch/gpsdio-segment

Segment a stream of messages into continuous tracks. 

For more information, see `module README <gpsdio_segment/README.md>`_.


Usage
-----

.. code-block:: console

    Usage: gpsdio segment [OPTIONS] INFILE OUTFILE

      Segment AIS data into continuous segments.

    Options:
      --version            Show the version and exit.
      --mmsi INTEGER       Only segment this MMSI.  If not given the first MMSI
                           found will be used.
      --max-hours FLOAT    Points with a time delta larger than N hours are forced
                           to be discontinuous. (default: 24)
      --max-speed FLOAT    Units are knots.  Points with a speed above this value
                           are always considered discontinuous. (default: 30)
      --noise-dist FLOAT   DEPRECATED. Units are nautical miles.  Points within this distance
                           are always considered continuous.  Used to allow a
                           certain amount of GPS noise. (default: 0.27)
      --segment-field TEXT Add the segment ID to this field when writing messages.
                           (default: segment)
      --help               Show this message and exit.


Installing
----------

.. code-block:: console

    $ git clone https://github.com/GlobalFishingWatch/gpsdio-segment
    $ pip install gpsdio-segment/


Developing
----------

.. code-block:: console

    $ git clone https://github.com/GlobalFishingWatch/gpsdio-segment
    $ cd gpsdio-segment
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -e .\[dev\]
    $ py.test tests --cov gpsdio_segment --cov-report term-missing

You can also use the docker environment if you don't want to use any dependency
on your machine. Just install `docker <https://www.docker.com/>`_ and `docker
compose <https://docs.docker.com/compose/`_ and then you can run development
commands inside the container by running this:

.. code-block:: console
    $ [sudo] docker-compose run dev py.test tests

Where `sudo` is used on Linux, but not on Mac.

Helpful Recipes
---------------

If you make changes and you know they are right, but test_cli.py is failing because the expectd output is now
different, you can update the expected output with this

.. code-block:: console
    gpsdio segment ./tests/data/416000000.json ./tests/data/segmented-416000000.json



To sort a newlineJSON file by timestamp
.. code-block:: console
    cat tests/data/416000000.json | jq -s -c '. | sort_by(.timestamp)[]'




License
-------

See ``LICENSE.txt``
