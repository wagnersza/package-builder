#! /usr/bin/python
# -*- coding: utf-8 -*-

import docker as docker_client
import os
import argparse
import subprocess
import sys
import dockerpty

parser = argparse.ArgumentParser(prog='package-builder', description='Make loca enviroment to build OS packages with docker')

parser.add_argument("-s", "--start", action="store_true", help="install and start local enviroment")
parser.add_argument("-b", "--build", action="store_true", help="build OS package")
parser.add_argument("-t", "--test", action="store_true", help="start shell with a clean container and copy package to test it") 
parser.add_argument("-i", "--image", default='centos:centos7', help="docker image, default: centos:centos7, see the options in https://registry.hub.docker.com") 

if len(sys.argv)==1:
    parser.print_help()
    sys.exit(1)

args = parser.parse_args()

def make_docker_file():
    file = open ('Dockerfile', 'w')
    file.write("FROM %s\n\n" % (args.image,))
    file.write("MAINTAINER Wagner Souza <wagnersza@gmail.com>\n\n")
    file.write("RUN yum install rpmdevtools wget -y\n")
    file.write("RUN yum groupinstall 'Development Tools' -y\n")
    file.write("RUN rpmdev-setuptree\n\n")
    file.close()
    return file

def add_build_require(rpm):
    file = open ('Dockerfile', 'a')
    file.write("\nRUN yum install -y %s\n" % (rpm,))
    file.close()
    # return file

def make_docker_file_test():
    test_dir = './test'
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)

    file = open ('./test/Dockerfile', 'w')
    file.write("FROM %s\n\n" % (args.image,))
    file.write("MAINTAINER Wagner Souza <wagnersza@gmail.com>\n\n")
    file.close()
    return file
    
def add_spec_to_file(spec_file):
    file = open ('Dockerfile', 'a')
    file.write("\nCOPY %s /rpmbuild/SPECS/\n" % (spec_file,))
    file.close()
    # return file

def add_source_to_file(source_files):
    file = open ('Dockerfile', 'a')
    file.write("\nADD %s /rpmbuild/SOURCES/\n" % (source_files,))
    file.close()


def main():
    shellinit = os.popen("boot2docker shellinit").read()
    env_docker_host = shellinit.strip().split("=")

    docker = docker_client.Client(base_url=env_docker_host[1],timeout=3000)
    # without parameters

    # Start: package-builder --start
    if args.start == True:
        print '\n - instaling boot2docker ...\n'
        os.system("brew install boot2docker")
        print '\n - starting boot2docker ...\n'
        os.system("boot2docker init")
        os.system("boot2docker up")
        print '\n - setting DOCKER_HOST env variable ...\n'
        os.putenv('DOCKER_HOST', env_docker_host[1]); os.system('bash')

    # Build: packege-builder --build
    if args.build == True:
        make_docker_file()

        # get spec file name
        ls = os.listdir(".")
        spec_file = filter(lambda x:'spec' in x, ls)

        # search for sources
        spec = open(spec_file[0], 'r').readlines()
        sources = filter(lambda x:'Source' in x, spec)
        
        # search for BuildRequire
        build_require = filter(lambda x:'BuildRequires' in x, spec)
        required_rpm = build_require[0].split()

        docker_lines = open('Dockerfile', 'r').readlines()
        
        # write on docker file
        for i in range(len(sources)):
            source_file = sources[i].split()
            source_line = filter(lambda x:source_file[1] in x, docker_lines)
            if source_line == []:
                add_source_to_file(source_file[1])

        for i in range(len(build_require)):
            build_require_line = build_require[i].split()
            add_build_require(build_require_line[1])
                
        spec_line = filter(lambda x:spec_file[0] in x, docker_lines)
        if spec_line == []:
            add_spec_to_file(spec_file[0]) # adiciona o nome do spec no Dockerfile

        # build docker image    
        os.system('docker build --tag="centos7:base_build" .')

        # create container
        container = docker.create_container(
            image='centos7:base_build',
            stdin_open=True,
            tty=True,
            command='/usr/bin/rpmbuild -ba /rpmbuild/SPECS/%s' % (spec_file[0],)
        )
        docker.start(container)
        dockerpty.PseudoTerminal(docker, container).start()
        
        # copy rpm to local directory
        docker_container = docker.containers(latest=True)
        container_id = docker_container[0]['Id']
        package_path = '/rpmbuild/RPMS'
        os.system('docker cp %s:/rpmbuild/RPMS .' % (container_id,))
        os.system('docker cp %s:/rpmbuild/SRPMS .' % (container_id,))

    # Test install: package-builder --test
    if args.test == True:
        make_docker_file_test()
        _ip = shellinit.strip().split(':')
        ip = _ip[1].split('//')[1]
        os.system('scp -r -i ~/.ssh/id_boot2docker RPMS SRPMS docker@%s:~/' % (ip,))
        os.system('docker build --tag="centos7:test" ./test')
        os.system('docker run -i -t -v /home/docker/RPMS:/RPMS -v /home/docker/SRPMS:/SRPMS centos7:test /bin/bash')

if __name__ == '__main__':
    main()