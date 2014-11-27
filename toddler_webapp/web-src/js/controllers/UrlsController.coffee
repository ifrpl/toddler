app = angular.module "toddlerWebApp"

app.controller "UrlsController",
  class UrlsController
    constructor: (@$scope, @locale, @$cookies, @$http, @dialogs, @$rootScope) ->

      _.extend @$scope,
        update_url_action: @update_url,
        delete_url_action: @delete_url

    update_url: =>
      @locale.ready(["common", "urls"]).then =>
        @dialogs.wait @locale.getString("common.pleaseWait"), @locale.getString("urls.pleaseWaitUpdatingUrl"), 33

        @$http.post "/api/v1/update-url", {url: @$scope.update_url}
        .success (response) =>
          @$rootScope.$broadcast 'dialogs.wait.progress', {'progress' : 100}
          @$rootScope.$broadcast 'dialogs.wait.complete'
        .error (response) =>
          @$rootScope.$broadcast 'dialogs.wait.complete'
          @dialogs.error(@locale.getString("common.error"), response.error)

    delete_url: =>
      @locale.ready(["common", "urls"]).then =>
        @dialogs.wait @locale.getString("common.pleaseWait"), @locale.getString("urls.pleaseWaitDeletingUrl"), 33
        @$http.post "/api/v1/delete-url", {url: @$scope.delete_url}
        .sucesss (response) =>
          @$rootScope.$broadcast 'dialogs.wait.progress', {'progress': 100}
          @$rootScope.$broadcast 'dialogs.wait.complete'
        .error (response) =>
          @$rootScope.$broadcast 'dialogs.wait.complete'
          @dialogs.error(@locale.getString("common.error"), response.error)


