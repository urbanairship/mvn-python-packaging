# Building Python Packages with Maven

As a new engineer at Urban Airship, one of my first tasks was to
improve our build process for generated Python code. Specifically, a
number of internal projects use [Maven](http://maven.apache.org) to
generate Java and Python bindings from specifications written using
Google's [Protocol
Buffers](https://developers.google.com/protocol-buffers/) language.

Initially, our existing Maven projects executed Google's `protoc`
compiler and placed the generated code in a sub-directory of the
current project. The resulting code was then copied to various other
projects as needed. After I finished updating them, our Maven projects
created a Python package containing the generated bindings, with a
version matching the corresponding JAR file, ready to upload to our
internal package distribution server. This article describes how I did
it.

Source files referenced in this article can be found in the [source
repository on
GitHub](https://github.com/urbanairship/mvn-python-packaging). The
version of the code matching the published version of this article is
tagged `TODO: tag source`. All source file references will be relative
to the git repository.

To execute the sample project, use the following command (the ``Using
Profiles to Disable Packaging'' section explains the reason for the
PYTHON_BINDINGS argument):

    mvn clean install -DPYTHON_BINDINGS

After Maven runs, you will find a Python package named ``sample_pb''
in `src/main/python/dist/sample-0.0.1.preview.tar.gz`. You will also
find the source for the package in `src/main/python/sample_pb`. 

## Project Structure

The project contains the following files and directories (following
Maven conventions):

  * pom.xml -- A Maven project file.
  * src/main/java -- Directory containing all Java source code.
  * src/main/python -- Directory containing all python source code.
  * src/main/resources -- Directory containing static resources used
  to build the project.

Normally, all compiled code is placed under the `target` directory. However,
this project generates code, so our outputs
ends up under `src/main/java` and `src/main/python`.

## Python Packages

A Python package consists of a single top-level
directory containing some number of Python source files, any number of
sub-directories, and a file named `__init__.py`.

The source from which a given package is built can take a number of
forms; for this project, I used the conventions given by
[`setuptools`](http://peak.telecommunity.com/DevCenter/setuptools). The
files for the package should be stored in a sub-directory named
`sample_pb`, and the top-level directory (in this case,
`src/main/python`) should contain three files: `MANIFEST.in`,
`setup.py`, and `requirements.txt`. Those three files, plus the
`sample_pb` sub-directory, are all that is needed to build and
distribute the `sample_pb` package.

## Maven Properties

I defined several properties in `pom.xml` to configure the Python
package that gets built. These include:

  * `python_package` -- The name of the package to build (in this case, ``sample_pb'').
  * `author`, `author_email`, `description`, `source_url` -- Authorship and documentation.

I also defined two other properties (`python_compile_phase` and
`python_deploy_phase`), which I discuss in the ``Using Profiles to
Disable Packaging'' section.

# Generating Protocol Buffer Bindings

The project generates Python and Java sources using Google's `protoc`
compiler. I used the [`exec`
plugin](http://mojo.codehaus.org/exec-maven-plugin/) to execute
`protoc` during the `generate-sources` phase. Later phases take the
genereated source code and turn it into a Python package. The
following snippet shows how the project executes `protoc`:

    <plugin>
      <artifactId>exec-maven-plugin</artifactId>
      ...
        <execution>
          ...
          <phase>generate-sources</phase>
          <goals><goal>exec</goal></goals>
          <configuration>
            <executable>protoc</executable>
            ...
            <arguments>
              ...
              <argument>
    --python_out=${basedir}/src/main/python/${python_package}</argument>
              <argument>${basedir}/src/main/resources/*.proto</argument>
            </arguments>
          </configuration>
        </execution>
      ...

`protoc` uses the `--python_out` argument to specify where generated
Python source goes; in the above, I used the `python_package` property
to make sure generated code gets placed in the `sample_pb` 
directory. In other words, `protoc` puts the generated code just
where I need it in order to build a package.

## Package Metadata

Metadata about the package comes from three files. Two should be found
in the `src/main/python` directory: `MANIFEST.in` and `setup.py`. The
third, `__init__.py`, is required to define a Python package, and
should be found in `src/main/python/sample_pb`. Optionally, `__init__.py`
can also include version infomration.

Each of these files contains specific information about the package
that may change with each build. For example, `__init__.py` should
match the version that appears in `pom.xml`. Because these files can
change on each build (and they are not automatically generated), I
used Maven's ``[filtered
resources](http://maven.apache.org/guides/getting-started/index.html#How_do_I_filter_resource_files)''
to create them.

Maven defines resources as files that are included in your project before
compilation, but are not compiled themselves. Resources are typically 
stored in `src/main/resources` and copied to another location within the
project before compilation. Maven can also ``filter'' these files, by 
performing a simple find-and-replace operation on their contents, before
copying them. Thus, ``filtered resources.''

Therefore, I placed `MANIFEST.in`, `setup.py` and `__init__.py` in
`src/main/resources`. I defined a `<resources>` section in `pom.xml`
that specifies the destination for each file. The files in
`src/main/resources` include references to Maven properties that will
be replaced with their actual value when the file is copied to its
final destination. For example, `MANIFEST.in` has these two lines:

    include requirements.txt
    include ${python_package}/*.proto

The text ```${python_package}`'' will be replaced by the value of the
`python_package` property, as specified in `pom.xml`. When Maven
copies this file to `src/main/python`, it will end up with these
contents:

    include requirements.txt
    include sample_pb/*.proto

Similar replacements occur with `__init__.py` and `setup.py`.

## Package Version Numbering

Our projects follow Java conventions, where ``pre-release''
libraries have the word ``SNAPSHOT'' appended to their version
number. For example, this project would be ``0.0.1-SNAPSHOT.''
[`setuptools` recommends a
scheme](http://peak.telecommunity.com/DevCenter/setuptools#specifying-your-project-s-version)
that uses both numeric versions and alphabetic conventions to indicate
different versions of a package. For this project, I choose to
translate ``SNAPSHOT'' versions into corresponding ``.preview''
versions. E.g., ``0.0.1-SNAPSHOT'' becomes ``0.0.1.preview''; for
released versions of a package, just the numeric version number is
used.

`pom.xml` already specifes a value for the project version (in the
`<version>` element); I wanted to the Python package to have the same
version. In order to do so, I used the `regex-property` goal provided
by the [build
helper](http://mojo.codehaus.org/build-helper-maven-plugin/)
plugin. This goal will assign a given property the result of
applying a regular expression to an input value. Below, you can see
the execution I defined to transform version numbers:

    <plugin>
      <groupId>org.codehaus.mojo</groupId>
      <artifactId>build-helper-maven-plugin</artifactId>
      ...
      <executions>
        <execution>
          <goals><goal>regex-property</goal></goals>
          <phase>generate-resources</phase>
          <configuration>
            <name>python_version</name>
            <regex>-SNAPSHOT</regex>
            <value>${project.version}</value>
            <replacement>\.preview</replacement>
            <failIfNoMatch>false</failIfNoMatch>
          </configuration>
        </execution>
      </executions>
    </plugin>

After the above executes, the `python_version` property will contain
the appropriate Python version. 

`__init__.py` and `setup.py` (in `src/main/resources`) both
refer to the `python_version` property. `__init__.py`:

    __version__ = '${python_version}'

and `setup.py`:

    setup(
        ...
        version='${python_version}',
        ...
    )

When Maven filters these resources (and copies them to
`src/main/python`), `${python_version}` will be replaced with the
correct version for the build. For example, because `pom.xml` sets the
version to `0.0.1-SNAPSHOT`, `__init__.py` ends up with these
contents:

    __version__ = '0.0.1.preview'

Even better, when a Maven ``release'' build is performed,
`__init__py` becomes:

    __version__ = '0.0.1'

This setup ensures that the version number of the Python package
always matches that found in `pom.xml`. 

## Building the Package

I use the Python interpreter to build the package, by having it execute
`setup.py` (in `src/main/python`) wiht an `sdist` argument. I use the `exec`
plugin to execute Python:

    <execution>
      <id>generate-package</id>
      <phase>compile</phase>
      <goals>
        <goal>exec</goal>
      </goals>
      <configuration>
        <executable>python</executable>
        <workingDirectory>${basedir}/src/main/python</workingDirectory>
        <arguments>
          <argument>setup.py</argument>
          <argument>sdist</argument>
        </arguments>
      </configuration>
    </execution>

This configuration is attached to the `compile` phase, which means it will
fire after all resources have been copied (and filtered) from `src/main/resources`
into `src/main/python`. 

##  Cleaning

Maven's [`clean`
plugin](http://maven.apache.org/plugins/maven-clean-plugin) deletes
files found under the directory specified by the `outputDirectory`
property (normally, `target/classes`). The settings I specified to
build the python package put code in the `src/main/python` directory,
but those files should still be deleted when `clean` is executed;
therefore, I specified additional directories and files that should be
removed. However, I could not just delete everything under
`src/main/python`, as I did not want to delete `requirements.txt`. By
using `<exclude>` tags, I can keep the files I want and delete all
others:

    <plugin>
      <artifactId>maven-clean-plugin</artifactId>
      ...
      <configuration>
        ...
            <directory>${basedir}/src/main/python</directory>
            <includes>
              <include>**/*</include>
              <include>*</include>
            </includes>
            <excludes>
              <exclude>requirements.txt</exclude>
            </excludes>
        ...
      </configuration>
    </plugin>


The notation `**/*` means to delete all files in all sub-directories,
recursively (except any excluded files). Therefore, all files except
`requirements.txt` are removed. 

# Using Profiles to Disable Packaging

When I first released a version of this project internally, I
immediately heard from other developers (who did not use the Python
bindings), that I had introduced a Python dependency into their local
builds. That wasn't acceptable to developers that only cared about the
generated Java bindings. However, I could not back these changes out
entirely, because we wanted these packages to be built on our CI
server, and we wanted the packages to stay in the same project as the
Protocol Buffer definitions.  In effect, I wanted to the Python
package to be built in three circumstances:

  * When I was developing (always)
  * When someone wanted to do a one-time build
  * When building the package under Jenkins

Maven [profiles](http://maven.apache.org/pom.html#Profiles) are
designed to address this situation. The developer can specify certain
conditions which, when met, add new settings and configuration to the
project definition. The effect is similar to conditionally inserting
blocks of XML.

I started using profiles but quickly found myself repeating large
chunks of configuration. Each profile can only match on one
condition. Therefore, for the the three conditions above, I needed to
repeat the same configuration. It wasn't maintainable.

In the section ``Building the Package, '' I showed a configuration
that executed Python during the `compile` phase, but in truth that is
not quite correct. Instead of using profiles to control the
configuration, I used profiles to set a property named
`python_compile_phase`. The actual definition that specifies how to
execute `protoc` then uses that property in the `<phase>` element, rather
than a fixed value:

     <execution>
       <id>generate-package</id>
       <phase>${python_compile_phase}</phase>
       <goals>
         <goal>exec</goal>
       </goals>
       ...
     </execution>

`python_compile_phase` is initially set to `never` (a non-existent
phase). If the property value doesn't change, then the configuration
shown above will not execute, because the `never` phase won't occur! I
then define profiles that changed the value of `python_compile_phase`
to `compile`, but only if certain command line flags or environment
variables were found. For example, this profile looks for
`-DPYTHON_BINDINGS` on the command-line:

    <id>python-builder</id>
    <activation>
      <property>
        <name>PYTHON_BINDINGS</name>
      </property>
    </activation>
    <properties>
      <python_compile_phase>compile</python_compile_phase>
    </properties>

Similar profiles look for environment variables named `PYTHON_BINDINGS`
and `JENKINS_URL`.

With this solution, I met my three goals. I could set the enviroment
variable `PYTHON_BINDINGS` on my local machine and always build
packages. On our CI server, `JENKINS_URL` will always be defined and
packages are built. Developers that don't want to build packages
don't have to do anything new -- the packages are not built by default.

# Future Improvements

I implemented the scheme described here over the course of several weeks
and multiple projects. By the end, I had found a way to define properties
in `pom.xml` such that I only needed to copy boilerplate files between 
projects (specifically, `setup.py`, `MANIFEST.in` and `__init__.py` in
`src/main/resources`). Otherwise, I just modified `pom.xml` for the
specific project. However, every time I found a way to improve this system, I
had to update multiple projects. A Maven plugin that handled these tasks is
an obvious next step.

The solution given here depends on a functioning Python installation, including
the right version of Google's Protocol Buffers package for Python. A way for
Maven to download (and verify) the correct packages would help make the solution
more robust.

Finally, I am not sure how future-proof it is to use a build phase that 
doesn't exist. It doesn't cause an error now, but in the future I'm not 
sure. Maybe it would be worth asking the Maven project to add a build
phase that never executes, just for this purpose?

