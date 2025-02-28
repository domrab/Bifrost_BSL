/*
There are two ways one can obtain the returned ports of a function.
One way is by providing a variable for each returned port, the other is
capture ever single port in a "NODE" type variable.
NODE type variable cannot be passed through scopes since they dont have a port
type equivalent in Bifrost. There isnt really all that much they can do at all.
*/

// create an overload for the scatter_points node
overload scatter_points(density_weights=FLOAT[], normal_override=FLOAT3[], tangent_override=FLOAT3[]);

compound return_SCATTER() {
    // lets consider a somewhat practical example. The create_mesh_plane node
    // has only one output "plane_mesh". We can
    // a) specify the port we want directly (only works for one port)
    OBJECT plane_direct = create_mesh_plane()->plane_mesh;

    // b) Use the walrus operator (:=) and assign a variable for each output port
    //    (in this case there is only one port, if there is more than on recipient
    //    on the left, the walrus operator is not required but good to have for
    //    clarity)
    OBJECT plane_mesh := create_mesh_plane();

    // c) Assign to a NODE type variable. Then, going forward you can access
    //    the port by calling mesh->plane_mesh (or whatever the output port
    //    name is you are trying to access)
    NODE mesh = create_mesh_plane();

    // to scatter points on a plane, same thing

    // direct
    OBJECT scatter_points = scatter_points(geometry=plane_direct)->points;

    // unpacking (I defined GEOLOCATION to look pretty here, if you are dealing
    // with types that dont have an alias, you can use the full type like so:
    // Geometry::Common::GeoLocation[] locations
    OBJECT points, FLOAT3[] positions, GEOLOCATION[] locations := scatter_points(geometry=plane_mesh);

    // by node
    NODE scatter = scatter_points(geometry=mesh->plane_mesh);

    // if there are output ports you dont care about, you can at any point
    // assign them to nothing:
    ..., FLOAT3[] positions2, ... := scatter_points(geometry=plane_mesh);

}
