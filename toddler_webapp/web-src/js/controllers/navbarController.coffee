app = angular.module "toddlerWebApp"

app.controller "NavbarController",
  class NavbarController
    constructor: (@$scope, @locale, @$cookies, @$http, @$location, @$rootScope) ->
      @$scope.logout = @logout

    logout: =>
      console.log "dupa"
      @$http.get("/api/v1/logout")
      .then (response) =>
        @$rootScope.logged_in = false
        @$location.path("/login")