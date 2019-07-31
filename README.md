# Visual Road: A Video Data Management Benchmark

Please see the [project website](http://visualroad.uwdb.io) for more details about the benchmark, links to the papers, sample videos, and pregenerated datasets.

## Synthetic Dataset Generation

1. Build the `ue4-docker:4.22.0` container using the [ue4-docker build instructions](https://adamrehn.com/docs/ue4-docker/read-these-first/introduction-to-ue4-docker).  Visual Road depends on Unreal version 4.22.0 and only supports Linux builds.
2. Clone the [Visual Road repository](https://github.com/uwdb/visualroad) and build the core docker container  
3. Using [docker-compose](https://docs.docker.com/compose) launch the docker container (e.g., `docker-compose run benchmark bash`)
4. Initiate dataset generation using `generator.py`.  For example, the following command generates a scale-1 dataset named `my-dataset`: `./generator.py --scale 1 my-dataset`.  
5. Execute `generator.py -h` for detailed help and other parameters (e.g., to specify resolution or duration).  
