app = angular.module "toddlerWebApp"

app.controller "LoginController",
  class LoginController
    constructor: (@$http, @$location, @$rootScope, @$scope) ->
      @$scope.login = @login
    login: =>
      @$http.post "/api/v1/login",
        user: @$scope.user
        password: @$scope.password
      .then (response) =>
        @$rootScope.logged_in = true
        if @$rootScope['_redirectAfterLogin'] isnt undefined
          redirect_path = @$rootScope._redirectAfterLogin
          @$rootScope._redirectAfterLogin = undefined
          @$location.path redirect_path
        else
          @$location.path "/"

