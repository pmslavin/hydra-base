#!/usr/bin/env python
# -*- coding: utf-8 -*-

# (c) Copyright 2013 to 2017 University of Manchester
#
# HydraPlatform is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HydraPlatform is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with HydraPlatform.  If not, see <http://www.gnu.org/licenses/>
#

import logging
log = logging.getLogger(__name__)

import json

from collections import defaultdict

from ..db.model import Attr,\
        Node,\
        Link,\
        ResourceGroup,\
        Network,\
        Project,\
        Scenario,\
        TemplateType,\
        ResourceAttr,\
        TypeAttr,\
        ResourceAttrMap,\
        ResourceScenario,\
        Dataset,\
        AttrGroup,\
        AttrGroupItem, \
        Dimension, \
        Unit
from .. import db
from sqlalchemy.orm.exc import NoResultFound
from ..exceptions import HydraError, ResourceNotFoundError
from ..util.permissions import required_perms, required_role
from sqlalchemy import or_, and_
from sqlalchemy.orm import aliased, joinedload
from . import units
from .objects import JSONObject

def _get_network(network_id):
    try:

        network_i = db.DBSession.query(Network).filter(Network.id==network_id).one()
    except NoResultFound:
        raise HydraError("Network %s not found" % (network_id))
    return network_i

def _get_project(project_id):
    try:

        project_i = db.DBSession.query(Project).filter(Project.id==project_id).one()
    except NoResultFound:
        raise HydraError("Project %s not found" % (project_id))
    return project_i


def _get_resource(ref_key, ref_id):
    try:
        if ref_key == 'NODE':
            return db.DBSession.query(Node).filter(Node.id == ref_id).one()
        elif ref_key == 'LINK':
            return db.DBSession.query(Link).filter(Link.id == ref_id).one()
        if ref_key == 'GROUP':
            return db.DBSession.query(ResourceGroup).filter(ResourceGroup.id == ref_id).one()
        elif ref_key == 'NETWORK':
            return db.DBSession.query(Network).filter(Network.id == ref_id).one()
        elif ref_key == 'SCENARIO':
            return db.DBSession.query(Scenario).filter(Scenario.id == ref_id).one()
        elif ref_key == 'PROJECT':
            return db.DBSession.query(Project).filter(Project.id == ref_id).one()
        else:
            return None
    except NoResultFound:
        raise ResourceNotFoundError("Resource %s with ID %s not found"%(ref_key, ref_id))

def _get_ra_resource(ra):
    ref_key = ra.ref_key
    try:
        if ref_key == 'NODE':
            return db.DBSession.query(Node).filter(Node.id == ra.node_id).one()
        elif ref_key == 'LINK':
            return db.DBSession.query(Link).filter(Link.id == ra.link_id).one()
        if ref_key == 'GROUP':
            return db.DBSession.query(ResourceGroup).filter(ResourceGroup.id == ra.group_id).one()
        elif ref_key == 'NETWORK':
            return db.DBSession.query(Network).filter(Network.id == ra.network_id).one()
        elif ref_key == 'SCENARIO':
            return db.DBSession.query(Scenario).filter(Scenario.id == ra.scenario_id).one()
        elif ref_key == 'PROJECT':
            return db.DBSession.query(Project).filter(Project.id == ra.project_id).one()
        else:
            return None
    except NoResultFound:
        raise ResourceNotFoundError("Resource found on resource attribute %s"%(ra))



def _get_resource_id(ra):
    ref_key = ra.ref_key
    if ref_key == 'NETWORK':
        return ra.network_id
    elif ref_key == 'NODE':
        return ra.node_id
    elif ref_key == 'LINK':
        return ra.link_id
    elif ref_key == 'GROUP':
        return ra.group_id
    elif ref_key == 'PROJECT':
        return ra.project_id

def get_attribute_by_id(attr_id, **kwargs):
    """
        Get a specific attribute by its ID.
    """
    try:
        attr_i = db.DBSession.query(Attr).filter(Attr.id==attr_id).one()
    except NoResultFound:
        raise ResourceNotFoundError("Attribute (attribute id=%s) does not exist"%(attr_id))

    return attr_i

def get_template_attributes(template_id, **kwargs):
    """
        Get a specific attribute by its ID.
    """

    try:
        attrs_i = db.DBSession.query(Attr).filter(TemplateType.template_id==template_id).filter(TypeAttr.type_id==TemplateType.id).filter(Attr.id==TypeAttr.id).all()
        log.debug(attrs_i)
        return attrs_i
    except NoResultFound:
        return None


def get_attribute_by_name_and_dimension(name, dimension_id=None,**kwargs):
    """
        Get a specific attribute by its name.
        dimension_id can be None, because in attribute the dimension_id is not anymore mandatory
    """
    try:
        attr_i = db.DBSession.query(Attr).filter(and_(Attr.name==name, Attr.dimension_id==dimension_id)).one()
        log.debug("Attribute retrieved")
        return attr_i
    except NoResultFound:
        return None

@required_role('admin')
def add_attribute_no_checks(attr,**kwargs):
    """
    ***WARNING*** This is used for test purposes only, and can allow
    duplicate attributes to be created
    """
    log.debug("Adding attribute: %s", attr.name)

    attr_i = Attr(name = attr.name, dimension_id = attr.dimension_id)
    attr_i.description = attr.description
    db.DBSession.add(attr_i)
    db.DBSession.flush()
    log.info("New attr added")
    return JSONObject(attr_i)



@required_perms('add_attribute')
def add_attribute(attr,**kwargs):
    """
    Add a generic attribute, which can then be used in creating
    a resource attribute, and put into a type.

    .. code-block:: python

        (Attr){
            id = 1020
            name = "Test Attr"
            dimension_id = 123
        }

    """
    log.debug("Adding attribute: %s", attr.name)

    try:
        attr_i = db.DBSession.query(Attr).filter(Attr.name == attr.name,
                                                 Attr.dimension_id == attr.dimension_id).one()
        log.info("Attr already exists")
    except NoResultFound:
        attr_i = Attr(name = attr.name, dimension_id = attr.dimension_id)
        attr_i.description = attr.description
        db.DBSession.add(attr_i)
        db.DBSession.flush()
        log.info("New attr added")
    return JSONObject(attr_i)

@required_perms('edit_attribute')
def update_attribute(attr,**kwargs):
    """
    Add a generic attribute, which can then be used in creating
    a resource attribute, and put into a type.

    .. code-block:: python

        (Attr){
            id = 1020
            name = "Test Attr"
            dimension_id = 123
        }

    """

    existing_attr_i = db.DBSession.query(Attr).filter(
        Attr.name == attr.name,
        Attr.dimension_id == attr.dimension_id,
        Attr.id != attr.id).first() #its ok if this is the one being updated!

    if existing_attr_i is not None:
        if attr.dimension_id is not None:
            dimension = units.get_dimension(attr.dimension_id)
            dimension_name = dimension.name
        else:
            dimension_name = 'None'

        raise HydraError(f"Cannot update attribute. An attribute with name {attr.name}"
                         f" and dimension {dimension_name} already exists with "
                         f"ID {existing_attr_i.id}")
    else:
        log.debug("Updating attribute: %s", attr.name)
        attr_i = _get_attr(attr.id)
        attr_i.name = attr.name
        attr_i.dimension_id = attr.dimension_id
        attr_i.description = attr.description

    db.DBSession.flush()
    return JSONObject(attr_i)


def delete_attribute(attr_id, **kwargs):
    try:
        attribute = db.DBSession.query(Attr).filter(Attr.id == attr_id).one()
        db.DBSession.delete(attribute)
        db.DBSession.flush()
        return True
    except NoResultFound:
        raise ResourceNotFoundError("Attribute (attribute id=%s) does not exist"%(attr_id))


def add_attributes(attrs,**kwargs):
    """
    Add a list of generic attributes, which can then be used in creating
    a resource attribute, and put into a type.

    .. code-block:: python

        (Attr){
            id = 1020
            name = "Test Attr"
            dimen = "very big"
        }

    """

    #Check to see if any of the attributs being added are already there.
    #If they are there already, don't add a new one. If an attribute
    #with the same name is there already but with a different dimension,
    #add a new attribute.

    # All existing attributes
    all_attrs = db.DBSession.query(Attr).all()
    attr_dict = {}
    for attr in all_attrs:
        attr_dict[(attr.name.lower(), attr.dimension_id)] = JSONObject(attr)

    attrs_to_add = []
    existing_attrs = []
    for potential_new_attr in attrs:
        if potential_new_attr is not None:
            # If the attrinute is None we cannot manage it
            log.debug("Adding attribute: %s", potential_new_attr)

            if attr_dict.get((potential_new_attr.name.lower(), potential_new_attr.dimension_id)) is None:
                attrs_to_add.append(JSONObject(potential_new_attr))
            else:
                existing_attrs.append(attr_dict.get((potential_new_attr.name.lower(), potential_new_attr.dimension_id)))

    new_attrs = []
    for attr in attrs_to_add:
        attr_i = Attr()
        attr_i.name = attr.name
        attr_i.dimension_id = attr.dimension_id
        attr_i.description = attr.description
        db.DBSession.add(attr_i)
        new_attrs.append(attr_i)

    db.DBSession.flush()


    new_attrs = new_attrs + existing_attrs

    return [JSONObject(a) for a in new_attrs]

def get_attributes(**kwargs):
    """
        Get all attributes
    """

    attrs = db.DBSession.query(Attr).order_by(Attr.name).all()

    return attrs

def _get_attr(attr_id):
    try:
        attr = db.DBSession.query(Attr).filter(Attr.id == attr_id).one()
        return attr
    except NoResultFound:
        raise ResourceNotFoundError("Attribute with ID %s not found"%(attr_id,))

def _get_templatetype(type_id):
    try:
        typ = db.DBSession.query(TemplateType).filter(TemplateType.id == type_id).one()
        return typ
    except NoResultFound:
        raise ResourceNotFoundError("Template Type with ID %s not found"%(type_id,))

def update_resource_attribute(resource_attr_id, is_var, **kwargs):
    """
        Deletes a resource attribute and all associated data.
    """
    user_id = kwargs.get('user_id')
    try:
        ra = db.DBSession.query(ResourceAttr).filter(ResourceAttr.id == resource_attr_id).one()
    except NoResultFound:
        raise ResourceNotFoundError("Resource Attribute %s not found"%(resource_attr_id))

    ra.check_write_permission(user_id)

    ra.is_var = is_var

    return 'OK'

def delete_resource_attribute(resource_attr_id, **kwargs):
    """
        Deletes a resource attribute and all associated data.
    """
    user_id = kwargs.get('user_id')
    try:
        ra = db.DBSession.query(ResourceAttr).filter(ResourceAttr.id == resource_attr_id).one()
    except NoResultFound:
        raise ResourceNotFoundError("Resource Attribute %s not found"%(resource_attr_id))

    ra.check_write_permission(user_id)
    db.DBSession.delete(ra)
    db.DBSession.flush()
    return 'OK'


def add_resource_attribute(resource_type, resource_id, attr_id, is_var, error_on_duplicate=True, **kwargs):
    """
        Add a resource attribute attribute to a resource.

        attr_is_var indicates whether the attribute is a variable or not --
        this is used in simulation to indicate that this value is expected
        to be filled in by the simulator.
    """

    attr = db.DBSession.query(Attr).filter(Attr.id==attr_id).first()

    if attr is None:
        raise ResourceNotFoundError("Attribute with ID %s does not exist."%attr_id)

    resource_i = _get_resource(resource_type, resource_id)

    resourceattr_qry = db.DBSession.query(ResourceAttr).filter(ResourceAttr.ref_key==resource_type)

    if resource_type == 'NETWORK':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.network_id==resource_id)
    elif resource_type == 'NODE':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.node_id==resource_id)
    elif resource_type == 'LINK':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.link_id==resource_id)
    elif resource_type == 'GROUP':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.group_id==resource_id)
    elif resource_type == 'PROJECT':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.project_id==resource_id)
    else:
        raise HydraError('Resource type "{}" not recognised.'.format(resource_type))
    resource_attrs = resourceattr_qry.all()

    for ra in resource_attrs:
        if ra.attr_id == attr_id:
            if not error_on_duplicate:
                return ra

            raise HydraError("Duplicate attribute. %s %s already has attribute %s"
                             %(resource_type, resource_i.get_name(), attr.name))

    attr_is_var = 'Y' if is_var == 'Y' else 'N'

    new_ra = resource_i.add_attribute(attr_id, attr_is_var)
    db.DBSession.flush()

    return new_ra

def add_resource_attrs_from_type(type_id, resource_type, resource_id,**kwargs):
    """
        adds all the attributes defined by a type to a node.
    """
    type_i = _get_templatetype(type_id)

    resource_i = _get_resource(resource_type, resource_id)

    resourceattr_qry = db.DBSession.query(ResourceAttr).filter(ResourceAttr.ref_key==resource_type)

    if resource_type == 'NETWORK':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.network_id==resource_id)
    elif resource_type == 'NODE':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.node_id==resource_id)
    elif resource_type == 'LINK':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.link_id==resource_id)
    elif resource_type == 'GROUP':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.group_id==resource_id)
    elif resource_type == 'PROJECT':
        resourceattr_qry = resourceattr_qry.filter(ResourceAttr.project_id==resource_id)

    resource_attrs = resourceattr_qry.all()

    attrs = {}
    for res_attr in resource_attrs:
        attrs[res_attr.attr_id] = res_attr

    new_resource_attrs = []
    for item in type_i.typeattrs:
        if attrs.get(item.attr_id) is None:
            ra = resource_i.add_attribute(item.attr_id)
            new_resource_attrs.append(ra)

    db.DBSession.flush()

    return new_resource_attrs

def get_all_network_resourceattributes(network_id, template_id=None, return_orm=False, **kwargs):
    """
        Get all the resource attributes for all the nodes, links and groups in the network
        including network attributes. This is used primarily to avoid retrieving
        all global attributes for menus etc, most of which are not necessary.

        args:
            network_id (int): The ID of the network containing the attributes
            template_id (int): A filter which will cause the function to
                                return attributes associated to that template
            return_orm (bool): Flag to force the function to return ORM objects instead
                                of JSONObjects, likely to be used internally from another
                                function

        returns:
            A list of Attributes as JSONObjects, with the
            additional data of 'attr_is_var'
            from its assocated ResourceAttribute. ex:
                {id:123,
                name: 'cost'
                dimension_id: 124,
                attr_is_var: 'Y' #comes from the ResourceAttr
                }
    """

    resource_attr_qry = db.DBSession.query(ResourceAttr).\
            join(Attr, ResourceAttr.attr_id==Attr.id).\
            outerjoin(Network, Network.id==ResourceAttr.network_id).\
            outerjoin(Node, Node.id==ResourceAttr.node_id).\
            outerjoin(Link, Link.id==ResourceAttr.link_id).\
            outerjoin(ResourceGroup, ResourceGroup.id==ResourceAttr.group_id).filter(
        or_(
            and_(ResourceAttr.network_id != None,
                    ResourceAttr.network_id == network_id),

            and_(ResourceAttr.node_id != None,
                    ResourceAttr.node_id == Node.id,
                                        Node.network_id==network_id),

            and_(ResourceAttr.link_id != None,
                    ResourceAttr.link_id == Link.id,
                                        Link.network_id==network_id),

            and_(ResourceAttr.group_id != None,
                    ResourceAttr.group_id == ResourceGroup.id,
                                        ResourceGroup.network_id==network_id)
        ))

    if template_id is not None:
        attr_ids = []
        rs = db.DBSession.query(TypeAttr).join(TemplateType,
                                            TemplateType.id==TypeAttr.type_id).filter(
                                                TemplateType.template_id==template_id).all()
        for r in rs:
            attr_ids.append(r.attr_id)

        resource_attr_qry = resource_attr_qry.filter(ResourceAttr.attr_id.in_(attr_ids))

    resource_attrs = resource_attr_qry.all()

    network_attributes = []
    for ra in resource_attrs:
        if return_orm is True:
            network_attributes.append(ra)
        else:
            ra_j = JSONObject(ra)
            ra_j.attr = JSONObject(ra.attr)
            network_attributes.append(ra_j)

    return network_attributes


def get_all_network_attributes(network_id, template_id=None, **kwargs):
    """
        Get all the attributes for all the nodes, links and groups in the network
        including network attributes. This is used primarily to avoid retrieving
        all global attributes for menus etc, most of which are not necessary.

        args:
            network_id (int): The ID of the network containing the attributes
            template_id (int): A filter which will cause the function to
                                return attributes associated to that template

        returns:
            A list of Attributes as JSONObjects, with the
            additional data of 'attr_is_var'
            from its assocated ResourceAttribute. ex:
                {id:123,
                name: 'cost'
                dimension_id: 124,
                attr_is_var: 'Y' #comes from the ResourceAttr
                }
        NOTE: This was originally done with a single query, but was split up for
              performamce reasons
    """

    network_attr_qry = db.DBSession.query(Attr, ResourceAttr.attr_is_var).\
            join(ResourceAttr, ResourceAttr.attr_id == Attr.id).\
            join(Network, Network.id == ResourceAttr.network_id).filter(
            and_(ResourceAttr.network_id != None,
                 ResourceAttr.network_id == network_id))
    network_attrs = network_attr_qry.all()

    node_attr_qry = db.DBSession.query(Attr, ResourceAttr.attr_is_var).\
            join(ResourceAttr, ResourceAttr.attr_id == Attr.id).\
            join(Node, Node.id == ResourceAttr.node_id).filter(
                and_(ResourceAttr.node_id is not None,
                 ResourceAttr.node_id == Node.id,
                 Node.network_id == network_id))
    node_attrs = node_attr_qry.all()

    link_attr_qry = db.DBSession.query(Attr, ResourceAttr.attr_is_var).\
            join(ResourceAttr, ResourceAttr.attr_id==Attr.id).\
            join(Link, Link.id == ResourceAttr.link_id).filter(
                and_(ResourceAttr.link_id is not None,
                 ResourceAttr.link_id == Link.id,
                 Link.network_id==network_id))
    link_attrs = link_attr_qry.all()

    group_attr_qry = db.DBSession.query(Attr, ResourceAttr.attr_is_var).\
            join(ResourceAttr, ResourceAttr.attr_id == Attr.id).\
            join(ResourceGroup, ResourceGroup.id == ResourceAttr.group_id).filter(
                and_(ResourceAttr.group_id is not None,
                 ResourceAttr.group_id == ResourceGroup.id,
                 ResourceGroup.network_id == network_id))

    group_attrs = group_attr_qry.all()

    resource_attrs = network_attrs + node_attrs + link_attrs + group_attrs

    if template_id is not None:
        log.info("Filtering out only attributes which appear in template %s", template_id)
        attr_ids = []
        rs = db.DBSession.query(TypeAttr).join(
            TemplateType,
            TemplateType.id == TypeAttr.type_id).filter(
            TemplateType.template_id == template_id).all()

        for r in rs:
            attr_ids.append(r.attr_id)
        filtered_results = []
        for ra in resource_attrs:
            if ra[0].id in attr_ids:
                filtered_results.append(ra)

        log.info("Filtered out %s attributes", len(resource_attrs)-len(filtered_results))

        resource_attrs = filtered_results


    network_attributes = []
    for ra in resource_attrs:
        attr_j = JSONObject(ra[0])
        attr_j.attr_is_var = ra[1]
        network_attributes.append(attr_j)

    return network_attributes

def get_all_resource_attributes(ref_key, network_id, template_id=None, **kwargs):
    """
        Get all the resource attributes for a given resource type in the network.
        That includes all the resource attributes for a given type within the network.
        For example, if the ref_key is 'NODE', then it will return all the attirbutes
        of all nodes in the network. This function allows a front end to pre-load an entire
        network's resource attribute information to reduce on function calls.
        If type_id is specified, only
        return the resource attributes within the type.
    """

    user_id = kwargs.get('user_id')

    resource_attr_qry = db.DBSession.query(ResourceAttr).\
            outerjoin(Node, Node.id==ResourceAttr.node_id).\
            outerjoin(Link, Link.id==ResourceAttr.link_id).\
            outerjoin(ResourceGroup, ResourceGroup.id==ResourceAttr.group_id).filter(
        ResourceAttr.ref_key == ref_key,
        or_(
            and_(ResourceAttr.node_id != None,
                    ResourceAttr.node_id == Node.id,
                                        Node.network_id==network_id),

            and_(ResourceAttr.link_id != None,
                    ResourceAttr.link_id == Link.id,
                                        Link.network_id==network_id),

            and_(ResourceAttr.group_id != None,
                    ResourceAttr.group_id == ResourceGroup.id,
                                        ResourceGroup.network_id==network_id)
        ))

    if template_id is not None:
        attr_ids = []
        rs = db.DBSession.query(TypeAttr).join(TemplateType,
                                            TemplateType.id==TypeAttr.type_id).filter(
                                                TemplateType.template_id==template_id).all()
        for r in rs:
            attr_ids.append(r.attr_id)

        resource_attr_qry = resource_attr_qry.filter(ResourceAttr.attr_id.in_(attr_ids))

    resource_attrs = resource_attr_qry.all()

    return resource_attrs

def get_resource_attributes(ref_key, ref_id, type_id=None, **kwargs):
    """
        Get all the resource attributes for a given resource.
        If type_id is specified, only
        return the resource attributes within the type.
    """

    user_id = kwargs.get('user_id')

    resource_attr_qry = db.DBSession.query(ResourceAttr).filter(
        ResourceAttr.ref_key == ref_key,
        or_(
            ResourceAttr.network_id==ref_id,
            ResourceAttr.node_id==ref_id,
            ResourceAttr.link_id==ref_id,
            ResourceAttr.group_id==ref_id
        ))

    if type_id is not None:
        attr_ids = []
        rs = db.DBSession.query(TypeAttr).filter(TypeAttr.type_id==type_id).all()
        for r in rs:
            attr_ids.append(r.attr_id)

        resource_attr_qry = resource_attr_qry.filter(ResourceAttr.attr_id.in_(attr_ids))

    resource_attrs = resource_attr_qry.all()

    return resource_attrs

def check_attr_dimension(attr_id, **kwargs):
    """
        Check that the dimension of the resource attribute data is consistent
        with the definition of the attribute.
        If the attribute says 'volume', make sure every dataset connected
        with this attribute via a resource attribute also has a dimension
        of 'volume'.
    """
    attr_i = _get_attr(attr_id)

    datasets = db.DBSession.query(Dataset).filter(Dataset.id == ResourceScenario.dataset_id,
                        ResourceScenario.resource_attr_id == ResourceAttr.id,
                        ResourceAttr.attr_id == attr_id).all()
    bad_datasets = []
    for d in datasets:
        if  attr_i.dimension_id is None and d.unit is not None or \
            attr_i.dimension_id is not None and d.unit is None or \
            units.get_dimension_by_unit_id(d.unit_id) != attr_i.dimension_id:
                # If there is an inconsistency
                bad_datasets.append(d.id)

    if len(bad_datasets) > 0:
        raise HydraError("Datasets %s have a different dimension_id to attribute %s"%(bad_datasets, attr_id))

    return 'OK'

def get_resource_attribute(resource_attr_id, **kwargs):
    """
        Get a specific resource attribte, by ID
        If type_id is Gspecified, only
        return the resource attributes within the type.
    """

    resource_attr_qry = db.DBSession.query(ResourceAttr).filter(
        ResourceAttr.id == resource_attr_id,
        )

    resource_attr = resource_attr_qry.first()

    if resource_attr is None:
        raise ResourceNotFoundError(f"Resource attribute {resource_attr_id} does not exist")

    return resource_attr

def set_attribute_mapping(resource_attr_a, resource_attr_b, **kwargs):
    """
        Define one resource attribute from one network as being the same as
        that from another network.
    """
    user_id = kwargs.get('user_id')
    ra_1 = get_resource_attribute(resource_attr_a)
    ra_2 = get_resource_attribute(resource_attr_b)

    mapping = ResourceAttrMap(resource_attr_id_a = resource_attr_a,
                             resource_attr_id_b  = resource_attr_b,
                             network_a_id     = ra_1.get_network().id,
                             network_b_id     = ra_2.get_network().id )

    db.DBSession.add(mapping)

    db.DBSession.flush()

    return mapping

def delete_attribute_mapping(resource_attr_a, resource_attr_b, **kwargs):
    """
        Define one resource attribute from one network as being the same as
        that from another network.
    """
    user_id = kwargs.get('user_id')

    rm = aliased(ResourceAttrMap, name='rm')

    log.info("Trying to delete attribute map. %s -> %s", resource_attr_a, resource_attr_b)
    mapping = db.DBSession.query(rm).filter(
                             rm.resource_attr_id_a == resource_attr_a,
                             rm.resource_attr_id_b == resource_attr_b).first()

    if mapping is not None:
        log.info("Deleting attribute map. %s -> %s", resource_attr_a, resource_attr_b)
        db.DBSession.delete(mapping)
        db.DBSession.flush()

    return 'OK'

def delete_mappings_in_network(network_id, network_2_id=None, **kwargs):
    """
        Delete all the resource attribute mappings in a network. If another network
        is specified, only delete the mappings between the two networks.
    """
    qry = db.DBSession.query(ResourceAttrMap).filter(or_(ResourceAttrMap.network_a_id == network_id, ResourceAttrMap.network_b_id == network_id))

    if network_2_id is not None:
        qry = qry.filter(or_(ResourceAttrMap.network_a_id==network_2_id, ResourceAttrMap.network_b_id==network_2_id))

    mappings = qry.all()

    for m in mappings:
        db.DBSession.delete(m)
    db.DBSession.flush()

    return 'OK'

def get_mappings_in_network(network_id, network_2_id=None, **kwargs):
    """
        Get all the resource attribute mappings in a network. If another network
        is specified, only return the mappings between the two networks.
    """
    qry = db.DBSession.query(ResourceAttrMap).filter(or_(ResourceAttrMap.network_a_id == network_id, ResourceAttrMap.network_b_id == network_id))

    if network_2_id is not None:
        qry = qry.filter(or_(ResourceAttrMap.network_a_id==network_2_id, ResourceAttrMap.network_b_id==network_2_id))

    return qry.all()

def get_node_mappings(node_id, node_2_id=None, **kwargs):
    """
        Get all the resource attribute mappings in a network. If another network
        is specified, only return the mappings between the two networks.
    """
    qry = db.DBSession.query(ResourceAttrMap).filter(
        or_(
            and_(
                ResourceAttrMap.resource_attr_id_a == ResourceAttr.id,
                ResourceAttr.node_id == node_id),
            and_(
                ResourceAttrMap.resource_attr_id_b == ResourceAttr.id,
                ResourceAttr.node_id == node_id)))

    if node_2_id is not None:
        aliased_ra = aliased(ResourceAttr, name="ra2")
        qry = qry.filter(or_(
            and_(
                ResourceAttrMap.resource_attr_id_a == aliased_ra.id,
                aliased_ra.node_id == node_2_id),
            and_(
                ResourceAttrMap.resource_attr_id_b == aliased_ra.id,
                aliased_ra.node_id == node_2_id)))

    return qry.all()

def get_link_mappings(link_id, link_2_id=None, **kwargs):
    """
        Get all the resource attribute mappings in a network. If another network
        is specified, only return the mappings between the two networks.
    """
    qry = db.DBSession.query(ResourceAttrMap).filter(
        or_(
            and_(
                ResourceAttrMap.resource_attr_id_a == ResourceAttr.id,
                ResourceAttr.link_id == link_id),
            and_(
                ResourceAttrMap.resource_attr_id_b == ResourceAttr.id,
                ResourceAttr.link_id == link_id)))

    if link_2_id is not None:
        aliased_ra = aliased(ResourceAttr, name="ra2")
        qry = qry.filter(or_(
            and_(
                ResourceAttrMap.resource_attr_id_a == aliased_ra.id,
                aliased_ra.link_id == link_2_id),
            and_(
                ResourceAttrMap.resource_attr_id_b == aliased_ra.id,
                aliased_ra.link_id == link_2_id)))

    return qry.all()


def get_network_mappings(network_id, network_2_id=None, **kwargs):
    """
        Get all the mappings of network resource attributes, NOT ALL THE MAPPINGS
        WITHIN A NETWORK. For that, ``use get_mappings_in_network``. If another network
        is specified, only return the mappings between the two networks.
    """
    qry = db.DBSession.query(ResourceAttrMap).filter(
        or_(
            and_(
                ResourceAttrMap.resource_attr_id_a == ResourceAttr.id,
                ResourceAttr.network_id == network_id),
            and_(
                ResourceAttrMap.resource_attr_id_b == ResourceAttr.id,
                ResourceAttr.network_id == network_id)))

    if network_2_id is not None:
        aliased_ra = aliased(ResourceAttr, name="ra2")
        qry = qry.filter(or_(
            and_(
                ResourceAttrMap.resource_attr_id_a == aliased_ra.id,
                aliased_ra.network_id == network_2_id),
            and_(
                ResourceAttrMap.resource_attr_id_b == aliased_ra.id,
                aliased_ra.network_id == network_2_id)))

    return qry.all()

def check_attribute_mapping_exists(resource_attr_id_source, resource_attr_id_target, **kwargs):
    """
        Check whether an attribute mapping exists between a source and target resource attribute.
        returns 'Y' if a mapping exists. Returns 'N' in all other cases.
    """
    qry = db.DBSession.query(ResourceAttrMap).filter(
                ResourceAttrMap.resource_attr_id_a == resource_attr_id_source,
                ResourceAttrMap.resource_attr_id_b == resource_attr_id_target).all()

    if len(qry) > 0:
        return 'Y'
    else:
        return 'N'


def get_attribute_group(group_id, **kwargs):
    """
        Get a specific attribute group
    """

    user_id=kwargs.get('user_id')

    try:
        group_i = db.DBSession.query(AttrGroup).filter(
                                            AttrGroup.id==group_id).one()
        group_i.project.check_read_permission(user_id)
    except NoResultFound:
        raise HydraError("Group %s not found" % (group_id,))

    return group_i


def add_attribute_group(attributegroup, **kwargs):
    """
        Add a new attribute group.

        An attribute group is a container for attributes which need to be grouped
        in some logical way. For example, if the 'attr_is_var' flag isn't expressive
        enough to delineate different groupings.

        an attribute group looks like:
            {
                'project_id' : XXX,
                'name'       : 'my group name'
                'description : 'my group description' (optional)
                'layout'     : 'my group layout'      (optional)
                'exclusive'  : 'N' (or 'Y' )          (optional, default to 'N')
            }
    """
    log.info("attributegroup.project_id %s",attributegroup.project_id) # It is None while it should be valued
    user_id=kwargs.get('user_id')
    project_i = db.DBSession.query(Project).filter(Project.id==attributegroup.project_id).one()
    project_i.check_write_permission(user_id)
    try:

        group_i = db.DBSession.query(AttrGroup).filter(
                                            AttrGroup.name==attributegroup.name,
                                            AttrGroup.project_id==attributegroup.project_id).one()
        log.info("Group %s already exists in project %s", attributegroup.name, attributegroup.project_id)

    except NoResultFound:

        group_i = AttrGroup()
        group_i.project_id  = attributegroup.project_id
        group_i.name        = attributegroup.name
        group_i.description = attributegroup.description
        group_i.layout      = attributegroup.get_layout()
        group_i.exclusive   = attributegroup.exclusive

        db.DBSession.add(group_i)
        db.DBSession.flush()

        log.info("Attribute Group %s added to project %s", attributegroup.name, attributegroup.project_id)

    return group_i

def update_attribute_group(attributegroup, **kwargs):
    """
        Add a new attribute group.

        An attribute group is a container for attributes which need to be grouped
        in some logical way. For example, if the 'attr_is_var' flag isn't expressive
        enough to delineate different groupings.

        an attribute group looks like:
            {
                'project_id' : XXX,
                'name'       : 'my group name'
                'description : 'my group description' (optional)
                'layout'     : 'my group layout'      (optional)
                'exclusive'  : 'N' (or 'Y' )          (optional, default to 'N')
            }
    """
    user_id=kwargs.get('user_id')

    if attributegroup.id is None:
        raise HydraError("cannot update attribute group. no ID specified")

    try:

        group_i = db.DBSession.query(AttrGroup).filter(AttrGroup.id==attributegroup.id).one()
        group_i.project.check_write_permission(user_id)

        layout = attributegroup.layout
        group_i.name        = attributegroup.name
        group_i.description = attributegroup.description
        group_i.layout = json.dumps(layout) if not isinstance(layout, str) else layout
        group_i.exclusive   = attributegroup.exclusive

        db.DBSession.flush()

        log.info("Group %s in project %s updated", attributegroup.id, attributegroup.project_id)
    except NoResultFound:

        raise HydraError('No Attribute Group %s was found in project %s', attributegroup.id, attributegroup.project_id)


    return group_i

def delete_attribute_group(group_id, **kwargs):
    """
        Delete an attribute group.
    """
    user_id = kwargs['user_id']

    try:

        group_i = db.DBSession.query(AttrGroup).filter(AttrGroup.id==group_id).one()

        group_i.project.check_write_permission(user_id)

        db.DBSession.delete(group_i)
        db.DBSession.flush()

        log.info("Group %s in project %s deleted", group_i.id, group_i.project_id)
    except NoResultFound:

        raise HydraError('No Attribute Group %s was found', group_id)


    return 'OK'

def get_network_attributegroup_items(network_id, **kwargs):
    """
        Get all the group items in a network
    """

    user_id=kwargs.get('user_id')


    net_i = _get_network(network_id)

    net_i.check_read_permission(user_id)

    group_items_i = db.DBSession.query(AttrGroupItem).filter(
                                    AttrGroupItem.network_id==network_id).all()

    return group_items_i

def get_group_attributegroup_items(network_id, group_id, **kwargs):
    """
        Get all the items in a specified group, within a network
    """
    user_id=kwargs.get('user_id')

    network_i = _get_network(network_id)

    network_i.check_read_permission(user_id)

    group_items_i = db.DBSession.query(AttrGroupItem).filter(
                                    AttrGroupItem.network_id==network_id,
                                    AttrGroupItem.group_id==group_id).all()

    return group_items_i


def get_attribute_item_groups(network_id, attr_id, **kwargs):
    """
        Get all the group items in a network with a given attribute_id
    """
    user_id=kwargs.get('user_id')

    network_i = _get_network(network_id)

    network_i.check_read_permission(user_id)

    group_items_i = db.DBSession.query(AttrGroupItem).filter(
                                        AttrGroupItem.network_id==network_id,
                                        AttrGroupItem.attr_id==attr_id).all()

    return group_items_i

def _get_attr_group(group_id):
    try:
        group_i = db.DBSession.query(AttrGroup).filter(AttrGroup.id==group_id).one()
    except NoResultFound:
        raise HydraError("Error adding attribute group item: group %s not found" % (agi.group_id))

    return group_i

def _get_attributegroupitems(network_id):
    existing_agis = db.DBSession.query(AttrGroupItem).filter(AttrGroupItem.network_id==network_id).all()
    return existing_agis

def add_attribute_group_items(attributegroupitems, **kwargs):

    """
        Populate attribute groups with items.
        ** attributegroupitems : a list of items, of the form:
            ```{
                    'attr_id'    : X,
                    'group_id'   : Y,
                    'network_id' : Z,
               }```

        Note that this approach supports the possibility of populating groups
        within multiple networks at the same time.

        When adding a group item, the function checks whether it can be added,
        based on the 'exclusivity' setup of the groups -- if a group is specified
        as being 'exclusive', then any attributes within that group cannot appear
        in any other group (within a network).
    """

    user_id = kwargs.get('user_id')

    if not isinstance(attributegroupitems, list):
        raise HydraError("Cannpt add attribute group items. Attributegroupitems must be a list")

    new_agis_i = []

    group_lookup = {}

    #for each network, keep track of what attributes are contained in which groups it's in
    #structure: {NETWORK_ID : {ATTR_ID: [GROUP_ID]}
    agi_lookup = {}

    network_lookup = {}

    #'agi' = shorthand for 'attribute group item'
    for agi in attributegroupitems:

        network_i = network_lookup.get(agi.network_id)

        if network_i is None:
            network_i = _get_network(agi.network_id)
            network_lookup[agi.network_id] = network_i

        network_i.check_write_permission(user_id)


        #Get the group so we can check for exclusivity constraints
        group_i = group_lookup.get(agi.group_id)
        if group_i is None:
            group_lookup[agi.group_id] = _get_attr_group(agi.group_id)

        network_agis = agi_lookup

        #Create a map of all agis currently in the network
        if agi_lookup.get(agi.network_id) is None:
            agi_lookup[agi.network_id] = {}
            network_agis = _get_attributegroupitems(agi.network_id)
            log.info(network_agis)
            for net_agi in network_agis:

                if net_agi.group_id not in group_lookup:
                    group_lookup[net_agi.group_id] = _get_attr_group(net_agi.group_id)

                if agi_lookup.get(net_agi.network_id) is None:
                    agi_lookup[net_agi.network_id][net_agi.attr_id] = [net_agi.group_id]
                else:
                    if agi_lookup[net_agi.network_id].get(net_agi.attr_id) is None:
                        agi_lookup[net_agi.network_id][net_agi.attr_id] = [net_agi.group_id]
                    elif net_agi.group_id not in agi_lookup[net_agi.network_id][net_agi.attr_id]:
                        agi_lookup[net_agi.network_id][net_agi.attr_id].append(net_agi.group_id)
        #Does this agi exist anywhere else inside this network?
        #Go through all the groups that this attr is in and make sure it's not exclusive
        if agi_lookup[agi.network_id].get(agi.attr_id) is not None:
            for group_id in agi_lookup[agi.network_id][agi.attr_id]:
                group = group_lookup[group_id]
                #Another group has been found.
                if group.exclusive == 'Y':
                    #The other group is exclusive, so this attr can't be added
                    raise HydraError("Attribute %s is already in Group %s for network %s. This group is exclusive, so attr %s cannot exist in another group."%(agi.attr_id, group.id, agi.network_id, agi.attr_id))

            #Now check that if this group is exclusive, then the attr isn't in
            #any other groups
            if group_lookup[agi.group_id].exclusive == 'Y':
                if len(agi_lookup[agi.network_id][agi.attr_id]) > 0:
                    #The other group is exclusive, so this attr can't be added
                    raise HydraError("Cannot add attribute %s to group %s. This group is exclusive, but attr %s has been found in other groups (%s)" % (agi.attr_id, agi.group_id, agi.attr_id, agi_lookup[agi.network_id][agi.attr_id]))


        agi_i = AttrGroupItem()
        agi_i.network_id = agi.network_id
        agi_i.group_id   = agi.group_id
        agi_i.attr_id    = agi.attr_id

        #Update the lookup table in preparation for the next pass.
        if agi_lookup[agi.network_id].get(agi.attr_id) is None:
            agi_lookup[agi.network_id][agi.attr_id] = [agi.group_id]
        elif agi.group_id not in agi_lookup[agi.network_id][agi.attr_id]:
            agi_lookup[agi.network_id][agi.attr_id].append(agi.group_id)


        db.DBSession.add(agi_i)

        new_agis_i.append(agi_i)
    log.info(agi_lookup)

    db.DBSession.flush()

    return new_agis_i

def delete_attribute_group_items(attributegroupitems, **kwargs):

    """
        remove attribute groups items .
        ** attributegroupitems : a list of items, of the form:
            ```{
                    'attr_id'    : X,
                    'group_id'   : Y,
                    'network_id' : Z,
               }```
    """


    user_id=kwargs.get('user_id')

    log.info("Deleting %s attribute group items", len(attributegroupitems))

    #if there area attributegroupitems from different networks, keep track of those
    #networks to ensure the user actually has permission to remove the items.
    network_lookup = {}

    if not isinstance(attributegroupitems, list):
        raise HydraError("Cannpt add attribute group items. Attributegroupitems must be a list")

    #'agi' = shorthand for 'attribute group item'
    for agi in attributegroupitems:

        network_i = network_lookup.get(agi.network_id)

        if network_i is None:
            network_i = _get_network(agi.network_id)
            network_lookup[agi.network_id] = network_i

        network_i.check_write_permission(user_id)

        agi_i = db.DBSession.query(AttrGroupItem).filter(AttrGroupItem.network_id == agi.network_id,
                                                 AttrGroupItem.group_id == agi.group_id,
                                                 AttrGroupItem.attr_id  == agi.attr_id).first()

        if agi_i is not None:
            db.DBSession.delete(agi_i)

    db.DBSession.flush()

    log.info("Attribute group items deleted")

    return 'OK'

@required_role('admin')
def delete_all_duplicate_attributes(**kwargs):
    """
        duplicate attributes can appear in the DB when attributes are added
        with a dimension of None (because mysql allows multiple entries
        even if there is a unique constraint where one of the values is null)

        This identifies one attribute of a duplicate set and then remaps all pointers to duplicates
        to that attribute, before deleting all other duplicate attributes.

        steps are:
            1: Identify all duplicate attributes
            2: Select one of the duplicates to be the one to keep
            3: Remap all resource attributes and type attributes to point from
               duplicate attrs to the keeper.
            4: Delete the duplicates.
    """

    #step 1: get all attributes and filter out the duplicates
    all_attributes = db.DBSession.query(Attr).all()

    #a lookup based on name/dimension (The apparent unique identifier for an attribute)
    attribute_lookup = defaultdict(lambda: [])
    for attribute in all_attributes:
        key = (attribute.name, attribute.dimension_id)
        attribute_lookup[key].append(attribute)

    #Now identify the dupes -- any of the dict's values which has a length > 1
    duplicate_attributes = filter(lambda x: len(x) > 1, attribute_lookup.values())

    for dupe_list in duplicate_attributes:
        log.info("Duplicate attributes found: name: %s, dimension: %s",
                 dupe_list[0].name, dupe_list[0].dimension_id)
        delete_duplicate_attributes(dupe_list)

    db.DBSession.flush()


@required_perms('delete_attribute', 'edit_network')
def delete_duplicate_resourceattributes(network_id=None, **kwargs):
    """
    for every resource, find any situations where there are duplicate attribute
    names, ex 2 max_flows, but where the attribute IDs are different. In this case,
    remove one of them, and keep the one which is used in the template for that node.
    """

    if network_id is None:
        #get all the resource attrs in the system -- but limit by only inputs
        all_ras = db.DBSession.query(ResourceAttr)\
            .filter(ResourceAttr.attr_is_var == 'N')\
            .options(joinedload('attr')).all()
    else:
        all_ras = get_all_network_resourceattributes(network_id, return_orm=True)

    #create a mapping for a node's resource attrs by its ID and the name of the attr
    ra_lookup = defaultdict(lambda: [])
    for ra in all_ras:
        key = (ra.ref_key, ra.get_resource_id(), ra.attr.name)
        ra_lookup[key].append(ra)

    duplicate_ra_list = filter(lambda x: len(x) > 1, ra_lookup.values())

    #we now have the duplicate resourceattrs. We need to identify which of them
    #to delete.
    for duplicate_ras in duplicate_ra_list:
        #first get the type of the resource
        resource = duplicate_ras[0].get_resource()
        #now get all the typeattrs defined for that resource
        resource_typeattrs = []
        for rt in resource.types:
            for ta in rt.get_templatetype().typeattrs:
                resource_typeattrs.append(ta.attr_id)

        data_to_transfer = {}
        ras_to_delete = []
        #now identify the attributes which are not defined in a typeattr, and
        #mark them for deletion
        for duplicate_ra in duplicate_ras:
            if duplicate_ra.attr_id not in resource_typeattrs:

                #we've found  a resource attribute not defined on the type.
                #Now check if there's data associated to it, and not the other.

                ra_rs = db.DBSession.query(ResourceScenario)\
                        .filter(ResourceScenario.resource_attr_id == duplicate_ra.id).first()

                #If this is the case, then remap the resource scenario to the RA
                #we wish to keep.
                if ra_rs is not None:
                    data_to_transfer[ra.attr.name] = ra_rs

                ras_to_delete.append(duplicate_ra)

        #None of the dupes are associated to a template, then delete any with
        #no data. Leave any with data, and let the user deal with them individually
        if len(ras_to_delete) == len(duplicate_ras):
            for ra_to_delete in ras_to_delete:
                ra_rs = db.DBSession.query(ResourceScenario)\
                        .filter(ResourceScenario.resource_attr_id == ra_to_delete.id).first()
                if ra_rs is None:
                    log.info("A duplicate found for %s on %s %s. Deleting as it has no data.",
                             ra_to_delete.attr.name,
                             ra_to_delete.ref_key,
                             resource.name)
                    db.DBSession.delete(ra_to_delete)
                else:
                    log.info("A duplicate found for %s on %s %s. Not deleting as it has data.",
                             ra_to_delete.attr.name,
                             ra_to_delete.ref_key,
                             resource.name)

            #no need to go further, so continue the outer loop
            continue

        #do a second pass, this time transferring data from the bad resourceattributes
        #to the keepers
        for duplicate_ra in duplicate_ras:
            #focus now on the keepers i.e. the ones defined in the template
            if duplicate_ra.attr_id in resource_typeattrs:
                ra_rs = db.DBSession.query(ResourceScenario)\
                    .filter(ResourceScenario.resource_attr_id == duplicate_ra.id).first()

                dupes_rs = data_to_transfer.get(ra.attr.name)
                if ra_rs is None:
                    #if this has no value, see if the dupe has a value and transfer it
                    if dupes_rs is not None:
                        log.info("Updating resource scenario with new reference to %s",
                                 duplicate_ra.attr.name)
                        newrs = ResourceScenario()
                        newrs.scenario_id = dupes_rs.scenario_id
                        newrs.resource_attr_id = duplicate_ra.id
                        newrs.dataset_id = dupes_rs.dataset_id
                        db.DBSession.add(newrs)
                else:
                    #delete any RS which are not needed
                    if dupes_rs is not None:
                        db.DBSession.delete(dupes_rs)


        #now finally delete all the dupes
        for ra_to_delete in ras_to_delete:

            log.info("Deleting resource attr %s (id: %s) from %s %s",\
                     duplicate_ra.attr.name,\
                     duplicate_ra.id,\
                     duplicate_ra.ref_key,\
                     resource.name)
            db.DBSession.delete(ra_to_delete)


def delete_duplicate_attributes(dupe_list):
    """
        Take a list of duplicate attributes and delete all but one.
        Steps are:
            1: Select one of the duplicates to keep
            2: Remap all resource attributes and type attributes to point
               from duplicate attrs to the keeper
            3: Delete the duplicates
        args:
            dupe_list: a list of iterables containing duplicate attributes
    """

    #sort by ID, and choose the attribute with the smallest ID to keep
    #The rationale being that this likely has the most existing references
    dupe_list.sort(key=lambda x: x.id)

    keeper = dupe_list[0]

    #remove all the rest in the list
    attrs_to_remove = dupe_list[1:]

    #remap all the attributes from those to delete to the keeper so they can be removed safely
    for attr_to_remove in attrs_to_remove:
        remap_attribute_reference(attr_to_remove.id, keeper.id)

        #now that the remapping is done, we can safely delete the old attribute
        delete_attribute(attr_to_remove.id)

    db.DBSession.flush()

    return keeper

def remap_attribute_reference(old_attr_id, new_attr_id, flush=False):
    """
        Remap everything which references old_attr_id to reference
        new_attr_id
    """
    #first, remap all the resource attributes
    ras_to_remap = db.DBSession.query(ResourceAttr)\
        .filter(ResourceAttr.attr_id == old_attr_id).all()

    deleted_ras = []
    for ra_to_remap in ras_to_remap:
        #is there an RA with the new attribute already on the same resource?
        existing_ra = db.DBSession.query(ResourceAttr)\
            .filter(ResourceAttr.attr_id == new_attr_id,
                    ResourceAttr.ref_key == ra_to_remap.ref_key,
                    ResourceAttr.node_id == ra_to_remap.node_id,
                    ResourceAttr.link_id == ra_to_remap.link_id,
                    ResourceAttr.group_id == ra_to_remap.group_id,
                    ResourceAttr.network_id == ra_to_remap.network_id).first()

        #if so, then it must be deleted so there is only one on the resource.
        if existing_ra is not None:
            #if the RA to be deleted is linked with data and the one to keep
            #is not, then remap the resource scenario.
            old_ra_rs = db.DBSession.query(ResourceScenario)\
                .filter(ResourceScenario.resource_attr_id == ra_to_remap.id).first()
            new_ra_rs = db.DBSession.query(ResourceScenario)\
                .filter(ResourceScenario.resource_attr_id == existing_ra.id).first()

            if old_ra_rs is not None and new_ra_rs is None:
                old_ra_rs.resource_attr_id = existing_ra.id

            #mark the RA as deleted so it can be ignored in the remapping
            #process later
            deleted_ras.append(ra_to_remap.id)
            db.DBSession.delete(ra_to_remap)


    for ra_to_remap in ras_to_remap:
        #no need to remap as it's been deleted
        if ra_to_remap.id in deleted_ras:
            continue
        ra_to_remap.attr_id = new_attr_id

    tas_to_remap = db.DBSession.query(TypeAttr)\
        .filter(TypeAttr.attr_id == old_attr_id).all()

    for ta_to_remap in tas_to_remap:
        #is there an existing type attr on the type with the same attr?
        existing_ta = db.DBSession.query(TypeAttr)\
            .filter(TypeAttr.attr_id == new_attr_id,
                    TypeAttr.type_id == ta_to_remap.type_id).first()

        #if so, delete it
        if existing_ta is not None:
            db.DBSession.delete(ta_to_remap)
        else:
            ta_to_remap.attr_id = new_attr_id

    if flush is True:
        db.DBSession.flush()
