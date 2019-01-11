import socket
import time

import docker as docker_module
from docker.errors import ImageNotFound

from tox import hookimpl


def escape_env_var(varname):
    """Uppercase and sanitize the env var name by replacing
        all invalid characters by an underscore.
    The result will match the following regex: [a-zA-Z_][a-zA-Z0-9_]*
    Example:
        my.private.registry/cat/image will become MY_PRIVATE_REGISTRY_CAT_IMAGE
    """
    varname = list(varname.upper())
    if not varname[0].isalpha():
        varname[0] = "_"
    for i, c in enumerate(varname):
        if not c.isalnum() and c != "_":
            varname[i] = "_"
    return "".join(varname)


@hookimpl
def tox_runtest_pre(venv):
    conf = venv.envconfig
    if not conf.docker:
        return

    docker = docker_module.from_env(version="auto")
    action = venv.session.newaction(venv, "docker")

    environment = {}
    for value in conf.dockerenv:
        envvar, _, value = value.partition("=")
        environment[envvar] = {value}
        venv.envconfig.setenv[envvar] = value

    mounts = {}
    for value in conf.dockervolumes:
        envvar, _, value = value.partition("=")
        mounts[envvar] = {"bind": value, "mode": "ro"}

    seen = set()
    for image in conf.docker:
        name, _, tag = image.partition(":")
        if name in seen:
            raise ValueError("Docker image {!r} is specified more than once".format(name))
        seen.add(name)

        try:
            docker.images.get(image)
        except ImageNotFound:
            action.setactivity("docker", "pull {!r}".format(image))
            with action:
                docker.images.pull(name, tag=tag or None)

    conf._docker_containers = []
    for image in conf.docker:
        name, _, tag = image.partition(":")

        action.setactivity("docker", "run {!r}".format(image))
        with action:
            container = docker.containers.run(
                image, detach=True, publish_all_ports=True, environment=environment, volumes=mounts
            )

        conf._docker_containers.append(container)

        container.reload()
        gateway_ip = container.attrs["NetworkSettings"]["Gateway"] or "0.0.0.0"
        for containerport, hostports in container.attrs["NetworkSettings"]["Ports"].items():
            hostport = None
            for spec in hostports:
                if spec["HostIp"] == "0.0.0.0":
                    hostport = spec["HostPort"]
                    break

            if not hostport:
                continue

            envvar = escape_env_var("{}_HOST".format(name))
            venv.envconfig.setenv[envvar] = gateway_ip

            envvar = escape_env_var("{}_{}".format(name, containerport))
            venv.envconfig.setenv[envvar] = hostport

            _, proto = containerport.split("/")
            if proto == "udp":
                continue

            # mostly-busy-loop until we can connect to that port; that
            # will be our signal that the container is ready (meh)
            start = time.time()
            while (time.time() - start) < 30:
                try:
                    sock = socket.create_connection(
                        # TODO: can`t use the gateway_ip, didn`t open a socket!
                        # address=(str(gateway_ip), int(hostport)),
                        address=("0.0.0.0", int(hostport)),
                        timeout=0.1,
                    )
                except socket.error:
                    time.sleep(0.1)
                else:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                    break
            else:
                raise Exception(
                    "Never got answer on container port: {} mapped to host port: {} from {}".format(
                        containerport, int(hostport), name
                    )
                )


@hookimpl
def tox_runtest_post(venv):
    conf = venv.envconfig
    if not hasattr(conf, "_docker_containers"):
        return

    action = venv.session.newaction(venv, "docker")

    for container in conf._docker_containers:
        action.setactivity("docker", "remove '{}' (forced)".format(container.short_id))
        with action:
            container.remove(force=True)


@hookimpl
def tox_addoption(parser):
    parser.add_testenv_attribute(
        name="docker",
        type="line-list",
        help="Name of docker images, including tag, to start before the test run",
        default=[],
    )
    parser.add_testenv_attribute(
        name="dockerenv",
        type="line-list",
        help="List of ENVVAR=VALUE pairs that will be passed to all containers",
        default=[],
    )
    parser.add_testenv_attribute(
        name="dockervolumes",
        type="line-list",
        help="List of ENVVAR=VALUE pairs that will be passed to all containers",
        default=[],
    )
