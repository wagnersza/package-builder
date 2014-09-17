#!/usr/bin/env python
 
import unittest
import os
from package_builder import package_builder

class TestPackageBuilder(unittest.TestCase):
    docker_image = "centos:centos7"
    lines = [        
        "FROM %s\n" % (docker_image,),
        'RUN yum install rpmdevtools wget -y\n',
        'RUN yum groupinstall "Development Tools" -y\n',
        'RUN rpmdev-setuptree\n',
    ]

    def clean(self):
        pass

    def setUp(self):
        test_dir = './test'
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)

    def tearDown(self):
        pass

    def test_make_docker_file_default(self):
        docker_file = "Dockerfile"
        if docker_file == 'Dockerfile':
            file_lines = self.lines
        else:
            file_lines = self.lines[0]

        package_builder.make_docker_file(docker_file, self.docker_image)
        with open(docker_file, "r") as f:
            read_file_lines = f.readlines()
    
        self.assertEqual(read_file_lines, file_lines)

    def test_make_docker_file_test(self):
        docker_file = "./test/Dockerfile"        
        if docker_file == 'Dockerfile':
            file_lines = self.lines
        else:
            file_lines = self.lines[0]

        package_builder.make_docker_file(docker_file, self.docker_image)
        with open(docker_file, "r") as f:
            lines = f.readlines()
            read_file_lines = lines[0]
    
        self.assertEqual(read_file_lines, file_lines)

        
if __name__ == '__main__':
	unittest.main()

