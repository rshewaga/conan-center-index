import os
from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration


class Jinja2cppConan(ConanFile):
    name = "jinja2cpp"
    license = "MIT"
    homepage = "https://jinja2cpp.dev/"
    url = "https://github.com/conan-io/conan-center-index"
    description = "Jinja2 C++ (and for C++) almost full-conformance template engine implementation"
    topics = ("conan", "cpp14", "cpp17", "jinja2", "string templates", "templates engine")
    exports_sources = "CMakeLists.txt", "patches/**"
    generators = "cmake", "cmake_find_package"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    _cmake = None

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        if self.settings.compiler.cppstd:
            tools.check_min_cppstd(self, 14)

    def requirements(self):
        self.requires("boost/1.74.0")
        self.requires("expected-lite/0.4.0")
        self.requires("fmt/6.2.1") # not compatible with fmt >= 7.0.0
        self.requires("optional-lite/3.2.0")
        self.requires("rapidjson/cci.20200410")
        self.requires("string-view-lite/1.4.0")
        self.requires("variant-lite/1.2.2")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = "Jinja2Cpp-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_cmake(self):
        if self._cmake:
            return self._cmake
        self._cmake = CMake(self)
        self._cmake.definitions["JINJA2CPP_BUILD_TESTS"] = False
        self._cmake.definitions["JINJA2CPP_STRICT_WARNINGS"] = False
        self._cmake.definitions["JINJA2CPP_BUILD_SHARED"] = self.options.shared
        self._cmake.definitions["JINJA2CPP_DEPS_MODE"] = "conan-build"
        self._cmake.definitions["JINJA2CPP_CXX_STANDARD"] = self.settings.compiler.get_safe("cppstd", 14)
        # Conan cmake generator omits the build_type flag for MSVC multiconfiguration CMake,
        # but provide build-type-specific runtime type flag. For now, Jinja2C++ build scripts
        # need to know the build type is being built in order to setup internal flags correctly
        self._cmake.definitions["CMAKE_BUILD_TYPE"] = self.settings.build_type
        compiler = self.settings.get_safe("compiler")
        if compiler == "Visual Studio":
            # Runtime type configuration for Jinja2C++ should be strictly '/MT' or '/MD'
            runtime = self.settings.get_safe("compiler.runtime")
            if runtime == "MTd":
                runtime = "MT"
            if runtime == "MDd":
                runtime = "MD"
            self._cmake.definitions["JINJA2CPP_MSVC_RUNTIME_TYPE"] = "/" + runtime
        self._cmake.configure(build_folder=self._build_subfolder)
        return self._cmake

    def build(self):
        if tools.Version(self.deps_cpp_info["fmt"].version) >= "7.0.0":
            raise ConanInvalidConfiguration("jinja2cpp requires fmt < 7.0.0")
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy("LICENSE", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "jinja2cpp"))
        tools.rmdir(os.path.join(self.package_folder, "share"))

    def package_info(self):
        # TODO: CMake imported target shouldn't be namespaced
        self.cpp_info.libs = ["jinja2cpp"]
