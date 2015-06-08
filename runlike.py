#!/usr/bin/env python

import click
from subprocess import check_output, STDOUT, CalledProcessError
from json import loads
import sys

def die(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)


class Inspector(object):
    def __init__(self, container, no_name, pretty):
        self.container = container
        self.no_name = no_name
        self.output = ""
        self.pretty = pretty

    def inspect(self):
        try:
            output = check_output("docker inspect %s" % self.container, stderr=STDOUT, shell=True)
            # print output
            self.facts = loads(output)
        except CalledProcessError, e:
            if "No such image or container" in e.output:
                die("No such container %s" % self.container)
            else:
                die(str(e))

    def get_fact(self, path):
        parts = path.split(".")
        value = self.facts[0]
        for p in parts:
            value = value[p]
        return value

    def format_cli(self):
        self.output = "docker run "

        image = self.get_fact("Config.Image")
        self.options = []

        name = self.get_fact("Name").split("/")[1]
        if not self.no_name:
            self.options.append("--name=%s" % name)

        envars = self.get_fact("Config.Env")
        if envars:
            for envar in envars:
                self.options.append('-e "%s"' % envar)

        volumes = self.get_fact("HostConfig.Binds")
        if volumes:
            for vol in volumes:
                self.options.append('-v "%s"' % vol)

        volumes_from = self.get_fact("HostConfig.VolumesFrom")
        if volumes_from:
            for vol in volumes_from:
                self.options.append('--volumes-from %s' % vol)

        ports = self.get_fact("NetworkSettings.Ports")
        if ports:
            for port_and_proto, options in ports.iteritems():
                host_ip = options[0]["HostIp"]
                host_port = options[0]["HostPort"]
                container_port = port_and_proto.split("/")[0]
                self.options.append('-p %s:%s:%s' % (host_ip, host_port, container_port))

        links = self.get_fact("HostConfig.Links")
        if links:
            for link in links:
                src, dst = link.split(":")
                dst = dst.split("/")[1]
                self.options.append('--link %s:%s' % (src, dst))

        # i didn't find anything other than AttachStderr/AttachStdin/AttachStdout to detect --detach
        stdout_attached = self.get_fact("Config.AttachStdout")
        if not stdout_attached:
            self.options.append("--detach=true")

        if self.get_fact("Config.Tty"):
            self.options.append('-t')

        parameters = ["run"]
        if len(self.options):
            parameters += self.options
        parameters.append(image)


        command = []
        cmd = self.get_fact("Config.Cmd")
        if cmd:
            command = " ".join(cmd)
        parameters.append(command)

        joiner = " "
        if self.pretty:
            joiner += "\\\n\t"
        parameters = joiner.join(parameters)

        return "docker %s" % parameters



@click.command(help="Shows command line necessary to run copy of existing Docker container.")
@click.argument("container")
@click.option("--no-name", is_flag=True, help="Do not include container name in output")
@click.option("-p", "--pretty", is_flag=True)
def cli(container, no_name, pretty):
    ins = Inspector(container, no_name, pretty)
    ins.inspect()
    print ins.format_cli()
    


def main():
    cli()

if __name__ == "__main__":
    main()
