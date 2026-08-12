#
# Copyright (c) Contributors to the Open 3D Engine Project.
# For complete copyright and license terms please see the LICENSE at the root of this distribution.
#
# SPDX-License-Identifier: Apache-2.0 OR MIT
#

# Fedora system-Qt6 swap for O3DE's bundled Qt (qt-6.10.2-rev8-linux).
# Copied to cmake/3rdParty/FindQt.cmake at %prep when --with system_qt6, so
# the engine's find_package(Qt ... MODULE COMPONENTS ...) resolves this
# instead of the CDN bundle. Adapted from
# o3de/3p-package-source:package-system/Qt/FindQt.cmake (+ Platform/Linux/*):
# the moc/uic/rcc/lrelease wrapper functions are ported verbatim (they only
# invoke the Qt host tools); the bundle-specific setup is replaced with a
# plain find_package(Qt6) against Fedora's qt6-qtbase-devel et al. Runtime
# plugins (platforms/imageformats/...) come from the distro qt6 packages at
# runtime (RPM Requires), so the bundle's plugin-copy deployment is dropped.

if(TARGET 3rdParty::Qt::Core) # Check we are not called multiple times
    return()
endif()

# Components the engine references (10 in engine code) plus the extras the
# bundle's Platform/Linux layer pulls in (DBus is a Widgets-plugin dep;
# GuiPrivate for the private headers AzQtComponents uses; OpenGL/LinguistTools
# are transitive/tooling). WaylandClient is intentionally omitted: it only fed
# the bundle's wayland plugin-copy, which we drop for the system swap (the
# Editor is XCB-forced on our target GPUs anyway).
set(QT6_COMPONENTS
    Core
    Concurrent
    DBus
    Gui
    GuiPrivate
    LinguistTools
    Network
    OpenGL
    OpenGLWidgets
    Svg
    SvgWidgets
    Test
    Widgets
    Xml
)

# Suppress the private-module version-tie warning (GuiPrivate).
set(QT_NO_PRIVATE_MODULE_WARNING ON)

# Qt only has debug and release; O3DE maps every non-debug config to release.
function(ly_qt_configuration_mapping in_config out_config)
    set(${out_config} RELEASE PARENT_SCOPE)
endfunction()

# Resolve Fedora's system Qt6 via config mode. qt6-qtbase-devel installs
# Qt6Config.cmake under the default CMake search prefixes, so no prefix hint
# is needed; find_package locates the distro Qt6 (6.10/6.11 across our
# chroots). NOTE: unlike the bundle, we deliberately do NOT pin the nested
# Qt package dirs -- resolving the system Qt6 everywhere is exactly the point.
find_package(Qt6
    COMPONENTS ${QT6_COMPONENTS}
    REQUIRED
    NO_CMAKE_PACKAGE_REGISTRY
)

# Wrap each component as 3rdParty::Qt::<C>, converting includes to SYSTEM
# includes so Qt headers don't trip the engine's -Werror, and mapping every
# config to Qt's release import. Aliasing config-mode Qt6:: targets is safe
# (they are real IMPORTED targets, not the stock-FindModule kind).
foreach(component ${QT6_COMPONENTS})
    if(TARGET Qt6::${component})

        get_target_property(system_includes Qt6::${component} INTERFACE_INCLUDE_DIRECTORIES)
        if(system_includes)
            set_target_properties(Qt6::${component} PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "")
            ly_target_include_system_directories(TARGET Qt6::${component}
                INTERFACE ${system_includes}
            )
        endif()

        add_library(3rdParty::Qt::${component} ALIAS Qt6::${component})
        mark_as_advanced(Qt6${component}_DIR)

        foreach(conf IN LISTS CMAKE_CONFIGURATION_TYPES)
            string(TOUPPER ${conf} UCONF)
            ly_qt_configuration_mapping(${UCONF} MAPPED_CONF)
            set_target_properties(Qt6::${component} PROPERTIES
                MAP_IMPORTED_CONFIG_${UCONF} ${MAPPED_CONF}
            )
        endforeach()

    endif()
endforeach()

mark_as_advanced(Qt6_DIR)
mark_as_advanced(Qt6CoreTools_DIR)
mark_as_advanced(Qt6GuiTools_DIR)
mark_as_advanced(Qt6WidgetsTools_DIR)
mark_as_advanced(Qt6LinguistTools_DIR)

# Translations + plugin wrapper targets the engine references. With system
# Qt6 the actual .qm/plugin .so files ship in the distro qt6 packages and are
# found at runtime, so these stay empty INTERFACE targets (no ly_add_target_files
# copy step -- the bundle needed it for a self-contained deploy; the RPM pulls
# the packages via Requires instead).
add_library(3rdParty::Qt::Core::Translations INTERFACE IMPORTED GLOBAL)
ly_add_dependencies(Qt6::Core 3rdParty::Qt::Core::Translations)

set(QT_PLUGINS
    Network
    Gui
    Widgets
)
foreach(plugin ${QT_PLUGINS})
    add_library(3rdParty::Qt::${plugin}::Plugins INTERFACE IMPORTED GLOBAL)
    ly_add_dependencies(Qt6::${plugin} 3rdParty::Qt::${plugin}::Plugins)
endforeach()

# Qt host tools. Prefer the imported-target locations that find_package(Qt6)
# provides (robust across chroots/arch: /usr/lib64 vs /usr/lib), fall back to
# find_program with the Fedora paths (moc/uic/rcc in the qt6 libexecdir;
# lrelease/lupdate in the qt6 bindir, also as *-qt6 in /usr/bin).
function(_o3de_qt_tool out_var imported_target prog_name)
    if(TARGET ${imported_target})
        get_target_property(_loc ${imported_target} IMPORTED_LOCATION)
        if(_loc AND EXISTS ${_loc})
            set(${out_var} ${_loc} CACHE FILEPATH "Qt tool ${prog_name}" FORCE)
            mark_as_advanced(${out_var})
            return()
        endif()
    endif()
    unset(${out_var} CACHE)
    find_program(${out_var} NAMES ${prog_name} ${prog_name}-qt6
        HINTS /usr/lib64/qt6/libexec /usr/lib/qt6/libexec /usr/lib64/qt6/bin /usr/lib/qt6/bin /usr/bin
        REQUIRED)
    mark_as_advanced(${out_var})
endfunction()

_o3de_qt_tool(QT_MOC_EXECUTABLE      Qt6::moc      moc)
_o3de_qt_tool(QT_UIC_EXECUTABLE      Qt6::uic      uic)
_o3de_qt_tool(AUTORCC_EXECUTABLE     Qt6::rcc      rcc)
_o3de_qt_tool(QT_LUPDATE_EXECUTABLE  Qt6::lupdate  lupdate)
_o3de_qt_tool(QT_LRELEASE_EXECUTABLE Qt6::lrelease lrelease)

# We don't use AUTOUIC, AUTOMOC or AUTORCC from cmake. They all use highly
# custom behavior which is hard to debug; instead we call the Qt generation
# executables directly. (Ported verbatim from the bundle's FindQt.cmake.)

#! ly_qt_uic_target: handles qt's ui files by injecting uic generation
#! You are expected to include the generated ui file in your code to use the generated classes
#! Output format is "YourFolder/ui_YourFileName.h"
function(ly_qt_uic_target TARGET all_ui_sources)
    list(FILTER all_ui_sources INCLUDE REGEX "^.*\\.ui$")
    if(NOT all_ui_sources)
        message(FATAL_ERROR "Target ${TARGET} contains AUTOUIC but doesnt have any .ui file")
        return()
    endif()

    if(AUTOGEN_BUILD_DIR)
        set(gen_dir ${AUTOGEN_BUILD_DIR})
    else()
        set(gen_dir ${CMAKE_CURRENT_BINARY_DIR}/${TARGET}_autogen/include)
    endif()

    foreach(ui_source ${all_ui_sources})
        get_filename_component(filename ${ui_source} NAME_WE)
        get_filename_component(dir ${ui_source} DIRECTORY)
        if(IS_ABSOLUTE ${dir})
            file(RELATIVE_PATH dir ${CMAKE_CURRENT_SOURCE_DIR} ${dir})
        endif()

        set(outfolder ${gen_dir}/${dir})
        set(outfile ${outfolder}/ui_${filename}.h)
        get_filename_component(infile ${ui_source} ABSOLUTE)

        file(MAKE_DIRECTORY ${outfolder})
        add_custom_command(OUTPUT ${outfile}
          COMMAND ${QT_UIC_EXECUTABLE} -o ${outfile} ${infile}
          MAIN_DEPENDENCY ${infile} VERBATIM
          COMMENT "UIC ${infile}"
        )

        set_source_files_properties(${infile} PROPERTIES SKIP_AUTOUIC TRUE)
        set_source_files_properties(${outfile} PROPERTIES
            SKIP_AUTOMOC TRUE
            SKIP_AUTOUIC TRUE
            SKIP_AUTORCC TRUE
            GENERATED TRUE
        )
        list(APPEND all_ui_wrapped_sources ${outfile})
    endforeach()

    target_sources(${TARGET} PRIVATE ${all_ui_wrapped_sources})
    source_group("Generated Files" FILES ${all_ui_wrapped_sources})

    get_property(has_includes TARGET ${TARGET} PROPERTY INCLUDE_DIRECTORIES SET)
    if(has_includes)
        get_property(all_include_directories TARGET ${TARGET} PROPERTY INCLUDE_DIRECTORIES)
        foreach(dir ${all_include_directories})
            if(IS_ABSOLUTE ${dir})
                file(RELATIVE_PATH dir ${CMAKE_CURRENT_SOURCE_DIR} ${dir})
            endif()
            list(APPEND new_includes ${gen_dir}/${dir})
        endforeach()
    endif()
    list(APPEND new_includes ${gen_dir})
    target_include_directories(${TARGET} PRIVATE ${new_includes})

endfunction()

#! ly_add_translations: adds translations (ts) to a target.
function(ly_add_translations)
    set(options)
    set(oneValueArgs TARGET)
    set(multiValueArgs FILES)

    cmake_parse_arguments(ly_add_translations "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    if(NOT ly_add_translations_TARGET)
        message(FATAL_ERROR "You must provide a target")
    endif()
    if(NOT ly_add_translations_FILES)
        message(FATAL_ERROR "You must provide at least a translation file")
    endif()

    if(AUTOGEN_BUILD_DIR)
        set(gen_dir ${AUTOGEN_BUILD_DIR})
    else()
        set(gen_dir ${CMAKE_CURRENT_BINARY_DIR}/${ly_add_translations_TARGET}_autogen/include)
    endif()

    set(stamp_file ${gen_dir}/update_translations_${ly_add_translations_TARGET}.stamp)
    add_custom_command(
        OUTPUT ${stamp_file}
        COMMAND ${QT_LUPDATE_EXECUTABLE}
            $<TARGET_PROPERTY:${ly_add_translations_TARGET},SOURCES>
            -ts ${ly_add_translations_FILES}
        WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}
        COMMAND_EXPAND_LISTS
        COMMAND ${CMAKE_COMMAND} -E touch ${stamp_file}
        COMMENT "Updating translation source files for ${ly_add_translations_TARGET}"
    )
    add_custom_target(update_translations_${ly_add_translations_TARGET}
        DEPENDS ${stamp_file}
    )
    set_target_properties(
        update_translations_${ly_add_translations_TARGET}
        PROPERTIES
            FOLDER "scripts/translations"
    )

    set(TRANSLATED_FILES)
    foreach(ts_file ${ly_add_translations_FILES})
        get_filename_component(infile ${ts_file} ABSOLUTE BASE_DIR ${CMAKE_CURRENT_LIST_DIR})
        get_filename_component(ts_name ${infile} NAME_WE)
        set(qm_file ${gen_dir}/${ts_name}.qm)
        add_custom_command(
            OUTPUT ${qm_file}
            COMMAND ${QT_LRELEASE_EXECUTABLE} ${infile} -qm ${qm_file}
            DEPENDS ${infile}
            COMMENT "Generating translation ${qm_file}"
            VERBATIM
        )
        list(APPEND TRANSLATED_FILES ${qm_file})
    endforeach()

    set(qrc_file_contents
"<RCC>
    <qresource prefix=\"Translations\">
")

    foreach(file ${TRANSLATED_FILES})
        get_filename_component(filename ${file} NAME)
        string(APPEND qrc_file_contents
"        <file>${filename}</file>
")
    endforeach()

    string(APPEND qrc_file_contents
"    </qresource>
</RCC>
")
    set(qrc_file_path ${gen_dir}/i18n_${ly_add_translations_TARGET}.qrc)
    file(WRITE ${qrc_file_path} ${qrc_file_contents})
    set_source_files_properties(
        ${TRANSLATED_FILES}
        ${qrc_file_path}
        PROPERTIES
            GENERATED TRUE
            SKIP_AUTORCC TRUE
    )

    target_sources(${ly_add_translations_TARGET} PRIVATE ${TRANSLATED_FILES})
    ly_qt_qrc_target(${ly_add_translations_TARGET} ${qrc_file_path})

endfunction()

#! ly_qt_qrc_target: handles qt's .qrc files
function(ly_qt_qrc_target TARGET all_qrc_sources)
    list(FILTER all_qrc_sources INCLUDE REGEX "^.*\\.qrc$")
    if(NOT all_qrc_sources)
        message("Target ${TARGET} contains AUTORCC but doesnt have any .qrc file")
        return()
    endif()

    if(AUTOGEN_BUILD_DIR)
        set(gen_dir ${AUTOGEN_BUILD_DIR})
    else()
        set(gen_dir ${CMAKE_CURRENT_BINARY_DIR}/${TARGET}_autogen/include)
    endif()

    foreach(qrc_source ${all_qrc_sources})
        get_filename_component(filename ${qrc_source} NAME_WE)
        get_filename_component(dir ${qrc_source} DIRECTORY)
        if(IS_ABSOLUTE ${dir})
            file(RELATIVE_PATH dir ${CMAKE_CURRENT_SOURCE_DIR} ${dir})
        endif()

        set(outfolder ${gen_dir}/${dir})
        set(outfile ${outfolder}/qrc_resources_${filename}.cpp)
        get_filename_component(infile ${qrc_source} ABSOLUTE)

        string(RANDOM _random)
        file(MAKE_DIRECTORY ${outfolder})
        add_custom_command(OUTPUT ${outfile}
          COMMAND ${AUTORCC_EXECUTABLE} -name ${filename} -o ${outfile} ${infile}
          MAIN_DEPENDENCY ${infile} VERBATIM
          COMMENT "RCC ${infile}"
        )

        set_source_files_properties(${infile} PROPERTIES SKIP_AUTORCC TRUE)
        set_source_files_properties(${outfile} PROPERTIES
            SKIP_AUTOMOC TRUE
            SKIP_AUTOUIC TRUE
            SKIP_AUTORCC TRUE
            SKIP_UNITY_BUILD_INCLUSION TRUE
            GENERATED TRUE
        )
        list(APPEND all_qrc_wrapped_sources ${outfile})
    endforeach()

    target_sources(${TARGET} PRIVATE ${all_qrc_wrapped_sources})
    source_group("Generated Files" FILES ${all_qrc_wrapped_sources})

    get_property(has_includes TARGET ${TARGET} PROPERTY INCLUDE_DIRECTORIES SET)
    if(has_includes)
        get_property(all_include_directories TARGET ${TARGET} PROPERTY INCLUDE_DIRECTORIES)
        foreach(dir ${all_include_directories})
            if(IS_ABSOLUTE ${dir})
                file(RELATIVE_PATH dir ${CMAKE_CURRENT_SOURCE_DIR} ${dir})
            endif()
            list(APPEND new_includes ${gen_dir}/${dir})
        endforeach()
    endif()
    list(APPEND new_includes ${gen_dir})
    target_include_directories(${TARGET} PRIVATE ${new_includes})

endfunction()

#! ly_qt_moc_target: handles qt's .h files by injecting moc generation
function(ly_qt_moc_target TARGET all_moc_sources)
    list(FILTER all_moc_sources INCLUDE REGEX "^.*\\.(h|hxx)$")
    if(NOT all_moc_sources)
        message("Target ${TARGET} contains AUTOMOC but doesn't have any Q_OBJECT macro in a .h or .hxx file")
        return()
    endif()

    if(AUTOGEN_BUILD_DIR)
        set(gen_dir ${AUTOGEN_BUILD_DIR})
    else()
        set(gen_dir ${CMAKE_CURRENT_BINARY_DIR}/${TARGET}_autogen/include)
    endif()

    foreach(moc_source ${all_moc_sources})
        file(READ ${moc_source} TMP)
        string(FIND "${TMP}" "Q_OBJECT" exist)
        if(${exist} EQUAL -1)
            continue()
        endif()

        get_filename_component(filename ${moc_source} NAME_WE)
        get_filename_component(dir ${moc_source} DIRECTORY)
        if(IS_ABSOLUTE ${dir})
            file(RELATIVE_PATH dir ${CMAKE_CURRENT_SOURCE_DIR} ${dir})
        endif()

        set(outfolder ${gen_dir}/${dir})
        set(outfile ${outfolder}/moc_${filename}.cpp)
        get_filename_component(infile ${moc_source} ABSOLUTE)

        file(MAKE_DIRECTORY ${outfolder})
        add_custom_command(OUTPUT ${outfile}
          COMMAND ${QT_MOC_EXECUTABLE} -o ${outfile} ${infile}
          MAIN_DEPENDENCY ${infile} VERBATIM
          COMMENT "MOC ${infile}"
        )

        set_source_files_properties(${infile} PROPERTIES SKIP_AUTOMOC TRUE)
        set_source_files_properties(${outfile} PROPERTIES
            SKIP_AUTOMOC TRUE
            SKIP_AUTOUIC TRUE
            SKIP_AUTORCC TRUE
            GENERATED TRUE
        )
        list(APPEND all_moc_wrapped_sources ${outfile})

    endforeach()

    target_sources(${TARGET} PRIVATE ${all_moc_wrapped_sources})
    source_group("Generated Files" FILES ${all_moc_wrapped_sources})

    get_property(has_includes TARGET ${TARGET} PROPERTY INCLUDE_DIRECTORIES SET)
    if(has_includes)
        get_property(all_include_directories TARGET ${TARGET} PROPERTY INCLUDE_DIRECTORIES)
        foreach(dir ${all_include_directories})
            if(IS_ABSOLUTE ${dir})
                file(RELATIVE_PATH dir ${CMAKE_CURRENT_SOURCE_DIR} ${dir})
            endif()
            list(APPEND new_includes ${gen_dir}/${dir})
        endforeach()
    endif()
    list(APPEND new_includes ${gen_dir})
    target_include_directories(${TARGET} PRIVATE ${new_includes})

endfunction()
