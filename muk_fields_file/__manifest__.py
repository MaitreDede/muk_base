###################################################################################
#
#    Copyright (c) 2017-2019 MuK IT GmbH.
#
#    This file is part of MuK Filestore Field
#    (see https://mukit.at).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

{
    "name": "MuK Filestore Field",
    "summary": """Filestore Support for Fields""",
    "version": "13.0.1.0.0",
    "category": "Extra Tools",
    "license": "LGPL-3",
    "website": "https://www.mukit.at",
    "author": "MuK IT",
    "contributors": ["Mathias Markl <mathias.markl@mukit.at>"],
    "depends": ["muk_fields_stream"],
    "images": ["static/description/banner.png"],
    "auto_install": False,
    "application": False,
    "installable": True,
    "post_load": "_patch_system",
}
