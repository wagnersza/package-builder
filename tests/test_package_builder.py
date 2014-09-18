"""
Docker-related utilities for building RPM packages.
"""

#!/usr/bin/env python

import unittest
import os
from package_builder import package_builder


class TestPackageBuilder(unittest.TestCase):
    "Package Builder TestCase"
    docker_image = "centos:centos7"
    lines = [
        "FROM %s\n" % (docker_image,),
        'RUN yum install rpmdevtools wget -y\n',
        'RUN yum groupinstall "Development Tools" -y\n',
        'RUN rpmdev-setuptree\n',
    ]

    def clean(self):
        "clean all"
        pass

    def setUp(self):
        "create ./test directory"
        test_dir = './test'
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)

    def tearDown(self):
        pass

    def test_docker_lines(self):
        "test docker lines"
        docker_image = "centos:centos7"
        lines = [
            "FROM %s\n" % (docker_image,),
            'RUN yum install rpmdevtools wget -y\n',
            'RUN yum groupinstall "Development Tools" -y\n',
            'RUN rpmdev-setuptree\n',
        ]
        self.assertEqual(lines, package_builder.file_lines(docker_image))

    def test_make_docker_file_rpmbuild(self):
        "test rpmbuild docker file content"
        docker_file = "Dockerfile"
        docker_image = "centos:centos7"
        package_builder.make_docker_file_rpmbuild(docker_file, docker_image)
        with open(docker_file, "r") as d_file:
            read_file_lines = d_file.readlines()
        self.assertEqual(read_file_lines, self.lines)

    def test_make_docker_file_default(self):
        "test default docker file content"
        docker_file = "./test/Dockerfile"
        docker_image = "centos:centos7"
        file_lines = package_builder.file_lines(docker_image)
        file_lines_read = file_lines[0]
        array = []
        array.insert(0, file_lines_read)
        package_builder.make_docker_file_default(docker_file, docker_image)
        with open(docker_file, "r") as d_file:
            read_file_lines = d_file.readlines()
        self.assertEqual(read_file_lines, array)


if __name__ == '__main__':
    unittest.main()
