OpenCORE
========

OpenCORE is a collection of collaboration utilities inspired by and integrating
elements of the `KARL Project <http://karlproject.org/>`_.

Functionality
=============

Database bootstrapping support
  Allows for first time initialisation of new databases and populates them with
  data, users and permissions.

Logging utilities
  Helpers for logging data coming from one or more application instance.

Password Gateway middleware
  Restrict user access to view the site by challenging all requests with an
  input requiring a generic password. This is stored as a cookie on the user
  machine to prevent the need to input this for each request.

Content model definitions
  Model definitions for various content types relating to; attachments, blogs,
  cataloging and indexing, commenting, syndication feeds and caching, community
  frameworks, file and image uploads, forums, "liking" content, static pages,
  user profiles, user to user messaging, content ordering, users and profiles.

Command-line scripting
  Utities for writing console scripts for managing the application database as
  well as a number of useful scripts covering; database evolution (migration),
  admin user management, catalog indexing and reindexing, renaming users and
  content.

Security
  Policy and definitions for user roles and permissions for certain actions on
  the system.

Tagging
  Tools and utilities for managing and maintaining tags on content within the
  system.

Testing
  Helper functions and utilities for unit testing elements of the application.

Utilities
  Utilities around sending email, pagination and batching, embedding content,
  image processing, syndication feed generation and content searching.

Views
  Generic views and templates to manage data objects and provide basic site
  structure.
  
JSON/JSONP API
  Support for formatted data structures to be provided per content type on
  data.json[p] and list.json[p] urls.
