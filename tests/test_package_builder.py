"""
Docker-related utilities for building RPM packages.
"""

#!/usr/bin/env python

import unittest
import os
from package_builder import package_builder


class TestPackageBuilder(unittest.TestCase):
    "Package Builder TestCase"

    docker_file_rpmbuild = 'Dockerfile'
    docker_file_default = './test/Dockerfile'
    docker_image = 'centos:centos7'
    spec_file = 'test.spec'
    source_file_0 = 'file0.tar.gz'
    source_file_1 = 'file1.tar.gz'
    build_require_0 = 'golang'
    build_require_1 = 'git'

    def clean(self):
        "clean all"
        if os.path.exists('./test'):
            os.remove("./test/Dockerfile")
            os.remove("./test")

        if os.path.exists("test.spec"):
            os.remove("test.spec")

    def make_spec_file(self):
        lines = [
            "Name:     tsuru\n",
            "Version:        0.6.2\n",
            "Release:        1\n",
            "Summary:        tsuru\n",
            "Group:          tsuru\n",
            "License:        https://github.com/tsuru/tsuru/blob/0.6.2/LICENSE\n",
            "URL:            http://www.tsuru.io\n",
            "Source0:        file0.tar.gz\n",
            "Source1:        file1.tar.gz\n",
            "BuildRoot:      %{_tmppath}/%{name}-server-%{version}-%{release}-root-%(%{__id_u} -n)\n",
            "BuildRequires:  golang\n\n",
            "BuildRequires:  git\n\n",
        ]
        with open("test.spec", "w") as s_file:
            s_file.writelines(lines)
    
    def make_docker_file(self):
        package_builder.make_docker_file_rpmbuild(self.docker_file_rpmbuild, self.docker_image)

    def tearDown(self):
        # self.clean()
        pass

    def setUp(self):
        "create ./test directory"
        test_dir = './test'
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        self.make_spec_file()
        
    def docker_image_lines(self):
        docker_image = "centos:centos7"
        lines = [
            "FROM %s\n" % (docker_image,),
            'RUN yum install rpmdevtools wget -y\n',
            'RUN yum groupinstall "Development Tools" -y\n',
            'RUN rpmdev-setuptree\n',
        ]
        return lines
    
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
        self.assertEqual(read_file_lines, self.docker_image_lines())

    def test_make_docker_file_default(self):
        "test default docker file content"
        docker_file = "./test/Dockerfile"
        docker_image = "centos:centos7"
        file_lines = package_builder.file_lines(docker_image)
        file_lines_read = file_lines[0]
        file_lines_list = []
        file_lines_list.insert(0, file_lines_read)
        package_builder.make_docker_file_default(docker_file, docker_image)
        with open(docker_file, "r") as d_file:
            read_file_lines = d_file.readlines()
        self.assertEqual(read_file_lines, file_lines_list)

    def test_get_spec_file_name(self):
        ""
        spec_file = "test.spec"
        package_builder.get_spec_file_name()
        self.assertEqual(package_builder.get_spec_file_name(), spec_file)

    def test_make_build_require_list(self):
        ""
        require = []
        require.append(self.build_require_0)
        require.append(self.build_require_1)
        require_list = package_builder.make_build_require_list()
        self.assertEqual(require_list, require)

    def test_make_source_list(self):
        ""
        source = []
        source.append(self.source_file_0)
        source.append(self.source_file_1)
        source_list = package_builder.make_source_list()
        self.assertEqual(source_list, source)

    def test_append_spec_file_to_docker_file(self):
        self.make_docker_file()
        package_builder.append_spec_file_to_docker_file()
        with open(self.docker_file_rpmbuild, "r") as docker_lines:
            docker_file_lines = docker_lines.readlines()
        spec_line = filter(lambda x:'spec' in x, docker_file_lines)
        line = ', '.join(spec_line)
        self.assertEqual(package_builder.spec_file_line(),line)

    def test_append_build_require_to_docker_file(self):
        self.make_docker_file()
        package_builder.append_build_require_to_docker_file()
        with open(self.docker_file_rpmbuild, "r") as docker_lines:
            docker_file_lines = docker_lines.readlines()
        self.assertIn("RUN yum install -y %s\n" % (package_builder.make_build_require_list()[0],), docker_file_lines)
        self.assertIn("RUN yum install -y %s\n" % (package_builder.make_build_require_list()[1],), docker_file_lines)
        

if __name__ == '__main__':
    unittest.main()
